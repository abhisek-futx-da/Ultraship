"""
Structured Data Extractor
Extracts structured shipment data from documents using LLM
"""

import os
import json
import re
import requests
from typing import Dict, Optional


class StructuredExtractor:
    """Extracts structured shipment data from logistics documents"""
    
    def __init__(self):
        self.llm_api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.llm_api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.llm_model = "openai/gpt-3.5-turbo"
        
        # Required fields for extraction
        self.required_fields = [
            "shipment_id",
            "shipper",
            "consignee",
            "pickup_datetime",
            "delivery_datetime",
            "booking_datetime",
            "equipment_type",
            "mode",
            "rate",
            "currency",
            "weight",
            "carrier_name"
        ]
    
    def extract(self, document_text: str) -> Dict:
        """
        Extract structured shipment data from document text
        
        Returns:
            Dict with all required fields (null if not found)
        """
        # Try LLM-based extraction first
        if self.llm_api_key:
            try:
                return self._extract_with_llm(document_text)
            except Exception as e:
                print(f"LLM extraction failed: {e}, falling back to rule-based")
        
        # Fallback to rule-based extraction
        return self._extract_with_rules(document_text)
    
    def _extract_with_llm(self, document_text: str) -> Dict:
        """Extract using LLM"""
        prompt = f"""Extract the following shipment information from this logistics document.
Return ONLY a valid JSON object with these exact fields. Use null for any missing values.

Required fields:
- shipment_id
- shipper
- consignee
- pickup_datetime
- delivery_datetime
- booking_datetime
- equipment_type
- mode
- rate
- currency
- weight
- carrier_name

Document text:
{document_text[:4000]}

Return only the JSON object, no other text:"""
        
        headers = {
            "Authorization": f"Bearer {self.llm_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.llm_model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 500
        }
        
        response = requests.post(self.llm_api_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        llm_output = result["choices"][0]["message"]["content"].strip()
        
        # Extract JSON from response
        try:
            # Try to find JSON object in response
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', llm_output, re.DOTALL)
            if json_match:
                extracted = json.loads(json_match.group())
            else:
                # Try parsing entire response as JSON
                extracted = json.loads(llm_output)
        except json.JSONDecodeError:
            # If JSON parsing fails, fall back to rule-based extraction
            print("LLM returned invalid JSON, falling back to rule-based extraction")
            return self._extract_with_rules(document_text)
        
        # Ensure all fields are present
        return self._normalize_extraction(extracted)
    
    # Words/phrases that indicate garbage extraction (sentence fragments, section headers, etc.)
    BLOCKLIST = frozenset([
        "details", "name", "info", "information", "contact", "phone", "amount", "agreed",
        "location", "during", "follow", "driver", "procedures", "cedures", "operating", "hours",
        "normal", "standard", "receiving", "demo", "powered", "tms", "page", "email", "from the",
        "follow on", "on-", "the shipper", "the consignee", "agreed amount", "—", "-"
    ])

    def _clean_value(self, s: Optional[str], max_len: int = 80) -> Optional[str]:
        """Trim and limit length; return None if looks like garbage."""
        if not s or not isinstance(s, str):
            return None
        s = s.strip()
        if len(s) > max_len:
            s = s[:max_len].strip()
        if len(s) < 2:
            return None
        return s if s else None

    def _reject_garbage(self, value: Optional[str], field: str) -> bool:
        """Return True if value should be rejected (blocklist, sentence fragment)."""
        if not value or len(value) < 2:
            return True
        v_lower = value.lower().strip()
        if v_lower in self.BLOCKLIST:
            return True
        for bad in self.BLOCKLIST:
            if len(bad) > 3 and bad in v_lower and len(v_lower) < 50:
                return True
        if field in ("shipper", "consignee", "carrier_name"):
            if any(x in v_lower for x in (" during ", " to follow", " location ", " procedures", " driver ", " operating ")):
                return True
            if v_lower.endswith(" on-") or " follow on" in v_lower:
                return True
        if field == "equipment_type" and any(x in v_lower for x in ("agreed", "amount", "rate")):
            return True
        if field == "carrier_name" and v_lower in ("details", "name", "carrier", "mc"):
            return True
        if field in ("pickup_datetime", "delivery_datetime"):
            if re.search(r'\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4}', value):
                return False
            if any(x in v_lower for x in (" from the ", " location ", " during ", " shipper ", " driver ", " normal ")):
                return True
        if field == "booking_datetime":
            if re.search(r'\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4}', value):
                return False
            if any(x in v_lower for x in ("procedures", " driver ", " follow ", "location")):
                return True
        return False

    def _extract_on_line(self, text: str, patterns: list, max_len: int = 80, reject_field: Optional[str] = None) -> Optional[str]:
        """Try each pattern; only capture on the same line; value from original text."""
        lines = text.split("\n")
        for line in lines:
            line_lower = line.lower()
            for pattern in patterns:
                match = re.search(pattern, line_lower, re.IGNORECASE)
                if match:
                    try:
                        if match.lastindex and match.lastindex >= 1:
                            result = line[match.start(1):match.end(1)].strip()
                        else:
                            result = line[match.start(0):match.end(0)].strip()
                    except (IndexError, AttributeError):
                        result = (match.group(1) if match.lastindex else match.group(0)).strip()
                    result = self._clean_value(result, max_len)
                    if result and (reject_field is None or not self._reject_garbage(result, reject_field)):
                        return result
        return None

    def _extract_with_rules(self, document_text: str) -> Dict:
        """Rule-based extraction: label-aware, line-bound, length-limited."""
        text_lower = document_text.lower()
        extracted = {}

        # Shipment ID: Load ID, Reference ID, BOL, etc.
        shipment_id_patterns = [
            r'\b(?:load|reference|ref)[\s_]*(?:id|#|number)?[\s:]+([A-Za-z0-9\-]{4,30})\b',
            r'\b(?:shipment|bol)[_\s]*(?:id|#|number)?[\s:]+([A-Za-z0-9\-]{4,30})\b',
            r'\bpro[\s_]*(?:id|#|number)[\s:]+([A-Za-z0-9\-]{4,30})\b',
            r'\b(?:bill\s+of\s+lading|bol)[\s#:]+([A-Za-z0-9\-]{4,30})\b',
        ]
        extracted["shipment_id"] = self._extract_on_line(document_text, shipment_id_patterns, 40)
        if extracted["shipment_id"]:
            if not re.match(r'^[A-Za-z0-9\-]+$', extracted["shipment_id"]):
                extracted["shipment_id"] = None
            elif extracted["shipment_id"].lower() in ("cedures", "procedures"):
                extracted["shipment_id"] = None
        # Fallback: Load ID on separate lines
        if not extracted["shipment_id"]:
            load_match = re.search(r'Load[\s\n]+ID[\s\n]+([A-Z0-9\-]{4,30})', document_text, re.IGNORECASE)
            if load_match:
                extracted["shipment_id"] = load_match.group(1)

        # Shipper: same line only; reject sentence fragments
        shipper_patterns = [
            r'shipper(?:\s+name)?[\s:]+([A-Za-z0-9\s\&,\.\-]+?)(?=\n|consignee|carrier|phone|address|$)',
            r'^\s*from[\s:]+([A-Za-z0-9\s\&,\.\-]{2,50}?)(?=\n|to\s|consignee|$)',
        ]
        extracted["shipper"] = self._extract_on_line(document_text, shipper_patterns, 60, "shipper")
        # Fallback: extract from Pickup section or after Shipper label
        if not extracted["shipper"]:
            # Try BOL format: "Shipper...1. AAA"
            shipper_match = re.search(r'Shipper.*?(\d+\.)[\s\n]+([A-Z][A-Za-z]+)', document_text, re.IGNORECASE | re.DOTALL)
            if shipper_match:
                result = self._clean_value(shipper_match.group(2), 60)
                if result and not self._reject_garbage(result, "shipper"):
                    extracted["shipper"] = result
            # Try Pickup section format
            if not extracted["shipper"]:
                pickup_match = re.search(r'Pickup[\s\n]+([A-Z][A-Za-z0-9\s\&,\.\-]+?)(?=\n)', document_text, re.IGNORECASE)
                if pickup_match:
                    result = self._clean_value(pickup_match.group(1), 60)
                    if result and not self._reject_garbage(result, "shipper"):
                        extracted["shipper"] = result

            # Try Pickup section format
            if not extracted["shipper"]:
                pickup_match = re.search(r'Pickup[\s\n]+([A-Z][A-Za-z0-9\s\&,\.\-]+?)(?=\n)', document_text, re.IGNORECASE)
                if pickup_match:
                    result = self._clean_value(pickup_match.group(1), 60)
                    if result and not self._reject_garbage(result, "shipper"):
                        extracted["shipper"] = result

            # Try Pickup section format
            elif not extracted["shipper"]:
                pickup_match = re.search(r'Pickup[\s\n]+([A-Z][A-Za-z0-9\s\&,\.\-]+?)(?=\n)', document_text, re.IGNORECASE)
                if pickup_match:
                    result = self._clean_value(pickup_match.group(1), 60)
                    if result and not self._reject_garbage(result, "shipper"):
                        extracted["shipper"] = result

        # Consignee: same line only; reject sentence fragments
        consignee_patterns = [
            r'consignee(?:\s+name)?[\s:]+([A-Za-z0-9\s\&,\.\-]+?)(?=\n|carrier|shipper|phone|address|$)',
            r'(?:deliver\s+to|^\s*to)[\s:]+([A-Za-z0-9\s\&,\.\-]{2,50}?)(?=\n|from\s|carrier|$)',
        ]
        extracted["consignee"] = self._extract_on_line(document_text, consignee_patterns, 60, "consignee")
        # Fallback: extract from Drop section or after Consignee label
        if not extracted["consignee"]:
            # Try BOL format: find second "1." for consignee (first is for shipper)
            matches = list(re.finditer(r'(\d+\.)[\s\n]+([a-z][a-z]+)', document_text, re.IGNORECASE))
            if len(matches) >= 2:
                result = self._clean_value(matches[1].group(2), 60)
                if result and not self._reject_garbage(result, "consignee"):
                    extracted["consignee"] = result
            # Try Drop section format
            if not extracted["consignee"]:
                drop_match = re.search(r'Drop[\s\n]+([a-z][a-z0-9\s\&,\.\-]+?)(?=\n)', document_text, re.IGNORECASE)
                if drop_match:
                    result = self._clean_value(drop_match.group(1), 60)
                    if result and not self._reject_garbage(result, "consignee"):
                        extracted["consignee"] = result


            # Try Drop section format
            elif not extracted["consignee"]:
                drop_match = re.search(r'Drop[\s\n]+([a-z][a-z0-9\s\&,\.\-]+?)(?=\n)', document_text, re.IGNORECASE)
                if drop_match:
                    result = self._clean_value(drop_match.group(1), 60)
                    if result and not self._reject_garbage(result, "consignee"):
                        extracted["consignee"] = result

        # Dates: prefer explicit date formats
        date_value = r'(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4}(?:\s+\d{1,2}:\d{2})?(?:\s*[ap]m)?|\d{4}[\-/]\d{2}[\-/]\d{2})'
        pickup_patterns = [
            r'(?:pickup|ship)(?:\s*(?:date|time|datetime))?[\s:]+' + date_value,
            r'shipping\s+date[\s:]+' + date_value,
            r'pickup[\s:]+([A-Za-z0-9\s,:\-]{3,40})',
        ]
        extracted["pickup_datetime"] = self._extract_on_line(document_text, pickup_patterns, 50, "pickup_datetime")
        # Fallback: Ship Date on separate lines
        if not extracted["pickup_datetime"]:
            ship_match = re.search(r'Ship[\s\n]+Date[\s\n]+(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4})', document_text, re.IGNORECASE)
            if ship_match:
                extracted["pickup_datetime"] = ship_match.group(1)

        delivery_patterns = [
            r'delivery(?:\s*(?:date|time|datetime))?[\s:]+' + date_value,
            r'delivery\s+date[\s:]+' + date_value,
            r'delivery\s+time[\s:]+([A-Za-z0-9\s,:\-]{3,50})',
        ]
        extracted["delivery_datetime"] = self._extract_on_line(document_text, delivery_patterns, 50, "delivery_datetime")
        # Fallback: extract from full text if not found on same line
        if not extracted["delivery_datetime"]:
            delivery_match = re.search(r'delivery\s+date[\s:\n]+(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4})', document_text, re.IGNORECASE)
            if delivery_match:
                extracted["delivery_datetime"] = delivery_match.group(1)

        booking_patterns = [
            r'booking(?:\s*(?:date|time|datetime))?[\s:]+' + date_value,
            r'booking[\s:]+(?:on\s+)?' + date_value,
            r'(?:booked|created)[\s:]+' + date_value,
            r'\bon\s+(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4}(?:\s+\d{1,2}:\d{2})?(?:\s*[ap]m)?)',
        ]
        raw_booking = self._extract_on_line(document_text, booking_patterns, 50, "booking_datetime")
        if raw_booking:
            raw_booking = re.sub(r'^\s*on\s+', '', raw_booking, flags=re.IGNORECASE).strip()
        extracted["booking_datetime"] = raw_booking

        # Equipment: single line; reject "Agreed Amount" etc.
        equipment_patterns = [
            r'equipment(?:\s+type)?[\s:]+([A-Za-z0-9\s\-]{2,25})',
            r'trailer\s+type[\s:]+([A-Za-z0-9\s\-]{2,25})',
            r'(flatbed|dry\s+van|reefer|step\s+deck|lowboy)[\s:]*\$',
        ]
        extracted["equipment_type"] = self._extract_on_line(document_text, equipment_patterns, 25, "equipment_type")

        # Mode: single word or two (e.g. LTL, FTL, Truckload)
        mode_patterns = [
            r'\bmode[\s:]+([A-Za-z]{2,20})\b',
            r'shipment\s+mode[\s:]+([A-Za-z]{2,20})',
            r'load\s+type[\s\n]+([A-Z]{2,3})\b',
        ]
        extracted["mode"] = self._extract_on_line(document_text, mode_patterns, 20)
        # Fallback: extract FTL/LTL from Load Type section
        if not extracted["mode"]:
            mode_match = re.search(r'Load Type[\s]*\n+([A-Z]{2,3})', document_text, re.IGNORECASE)
            if mode_match:
                extracted["mode"] = mode_match.group(1)

        # Rate: number only (with optional $ and commas)
        rate_patterns = [
            r'(?:rate|amount)[\s:]*\$?\s*([0-9,]+\.?[0-9]*)',
            r'\$\s*([0-9,]+\.?[0-9]+)',
        ]
        rate_str = self._extract_on_line(document_text, rate_patterns, 15)
        if rate_str:
            rate_str = rate_str.replace(",", "").replace("$", "").strip()
        extracted["rate"] = float(rate_str) if rate_str and re.match(r'^[0-9.]+$', rate_str) else None

        # Currency
        currency_patterns = [
            r'currency[\s:]+([A-Z]{3})\b',
            r'\b(usd|eur|gbp)\b',
        ]
        currency = self._extract_on_line(document_text, currency_patterns, 5) or self._extract_pattern(text_lower, [r'\b(usd|eur|gbp)\b'])
        extracted["currency"] = (currency or "USD").upper() if currency else "USD"

        # Weight: number + optional unit
        weight_patterns = [
            r'weight[\s:]+([0-9,]+\.?[0-9]*)[\s]*(?:lbs?|kg|pounds?)?',
            r'([0-9,]+\.?[0-9]+)\s*lbs?\b',
            r'([0-9,]+\.?[0-9]*)\s*(?:lbs?|pounds?)\s*(?:weight|$)',
        ]
        weight_str = self._extract_on_line(document_text, weight_patterns, 20)
        if weight_str:
            weight_str = re.sub(r'[^\d.]', '', weight_str.replace(",", ""))
        extracted["weight"] = float(weight_str) if weight_str and re.match(r'^[0-9.]+$', weight_str) else None
        # Fallback: weight on separate line
        if not extracted["weight"]:
            weight_match = re.search(r'(\d+)[\s\n]+lbs', document_text, re.IGNORECASE)
            if weight_match:
                extracted["weight"] = float(weight_match.group(1))

        # Carrier name: same line, bounded; reject "Details", "Name", etc.
        carrier_patterns = [
            r'carrier(?:\s+name)?[\s:]+([A-Za-z0-9\s\&,\.\-]+?)(?=\n|mc\s|phone|equipment|rate|details|$)',
            r'carrier[\s:]+([A-Za-z0-9\s\&,\.\-]{2,50})',
        ]
        extracted["carrier_name"] = self._extract_on_line(document_text, carrier_patterns, 50, "carrier_name")
        # Fallback: extract from Accepted by section or Customer name
        if not extracted["carrier_name"]:
            carrier_match = re.search(r'Accepted by[\s\n]+([A-Z][A-Za-z]+?)(?=\s+Date|\s+Signature|\n)', document_text, re.IGNORECASE)
            if carrier_match and carrier_match.group(1).lower() not in ('date', 'signature'):
                result = self._clean_value(carrier_match.group(1), 50)
                if result and not self._reject_garbage(result, "carrier_name"):
                    extracted["carrier_name"] = result
            if not extracted["carrier_name"]:
                customer_match = re.search(r'Customer[\s]+([A-Z][A-Za-z\s]+?)(?=\s+Contact|\n)', document_text, re.IGNORECASE)
                if customer_match:
                    result = self._clean_value(customer_match.group(1), 50)
                    if result and result.lower() not in ('details', 'contact'):
                        extracted["carrier_name"] = result

        return self._normalize_extraction(extracted)
    
    def _extract_pattern(self, text: str, patterns: list, default: Optional[str] = None) -> Optional[str]:
        """Extract first match from patterns (uses group(1) if present, else group(0))"""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result = match.group(0).strip()
                try:
                    if match.lastindex and match.lastindex >= 1:
                        g1 = match.group(1)
                        if g1 and str(g1).strip():
                            result = str(g1).strip()
                except (IndexError, AttributeError, TypeError):
                    pass
                if result:
                    return result
        return default
    
    def _normalize_extraction(self, extracted: Dict) -> Dict:
        """Ensure all required fields are present with null defaults"""
        normalized = {}
        for field in self.required_fields:
            val = extracted.get(field)
            normalized[field] = val if val is not None and val != "" else None
        return normalized
