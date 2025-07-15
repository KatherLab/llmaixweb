import re
from typing import Any, Dict, List

import pandas as pd
from pandas.errors import ParserError
from thefuzz import fuzz


class FieldMapper:
    """Intelligent field mapping between schema and ground truth."""

    def __init__(self):
        self.type_patterns = {
            "date": [r"\d{4}-\d{2}-\d{2}", r"\d{2}/\d{2}/\d{4}", r"\d{2}-\d{2}-\d{4}"],
            "number": [r"^-?\d+\.?\d*$", r"^-?\d+,\d+$"],
            "boolean": [r"^(true|false|yes|no|y|n|0|1)$"],
            "email": [r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"],
            "phone": [r"^\+?\d{10,15}$", r"^\(\d{3}\)\s*\d{3}-\d{4}$"],
        }

        self.common_mappings = {
            "id": ["document_id", "doc_id", "file_id", "record_id"],
            "name": ["full_name", "person_name", "customer_name"],
            "date": ["created_date", "creation_date", "timestamp"],
            "amount": ["total", "sum", "price", "cost"],
            "email": ["email_address", "mail", "contact_email"],
            "phone": ["phone_number", "telephone", "mobile", "contact_number"],
            "address": ["street_address", "location", "addr"],
            "description": ["desc", "details", "notes", "comments"],
        }

    def auto_map(
        self,
        schema_fields: Dict[str, str],
        ground_truth_fields: Dict[str, List[Any]],
        confidence_threshold: float = 0.7,
    ) -> List[Dict]:
        """Automatically map fields based on names and values."""

        mappings = []

        for schema_field, schema_type in schema_fields.items():
            best_match = None
            best_score = 0

            for gt_field, gt_values in ground_truth_fields.items():
                # Calculate name similarity
                name_score = self._calculate_name_similarity(schema_field, gt_field)

                # Calculate value compatibility
                value_score = self._calculate_value_compatibility(
                    schema_type, gt_values
                )

                # Combined score
                total_score = (name_score * 0.6) + (value_score * 0.4)

                if total_score > best_score:
                    best_score = total_score
                    best_match = gt_field

            if best_match and best_score >= confidence_threshold:
                # Determine comparison method
                comparison_method = self._get_comparison_method(
                    schema_type, ground_truth_fields[best_match]
                )

                mappings.append(
                    {
                        "schema_field": schema_field,
                        "ground_truth_field": best_match,
                        "field_type": schema_type,
                        "comparison_method": comparison_method,
                        "confidence": best_score,
                        "comparison_options": self._get_comparison_options(
                            schema_type, comparison_method
                        ),
                    }
                )

        return sorted(mappings, key=lambda x: x["confidence"], reverse=True)

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between field names."""

        # Normalize names
        name1 = self._normalize_field_name(name1)
        name2 = self._normalize_field_name(name2)

        # Exact match
        if name1 == name2:
            return 1.0

        # Check common mappings
        for key, variants in self.common_mappings.items():
            if name1 == key and name2 in variants:
                return 0.9
            if name2 == key and name1 in variants:
                return 0.9

        # Fuzzy matching
        ratio = fuzz.ratio(name1, name2) / 100.0
        partial_ratio = fuzz.partial_ratio(name1, name2) / 100.0
        token_sort_ratio = fuzz.token_sort_ratio(name1, name2) / 100.0

        return max(ratio, partial_ratio, token_sort_ratio)

    def _normalize_field_name(self, name: str) -> str:
        """Normalize field name for comparison."""

        # Convert to lowercase
        name = name.lower()

        # Replace underscores and hyphens with spaces
        name = re.sub(r"[_-]", " ", name)

        # Remove common prefixes/suffixes
        name = re.sub(r"^(the|a|an)\s+", "", name)
        name = re.sub(r"\s+(id|number|num|no)$", "", name)

        # Remove extra spaces
        name = " ".join(name.split())

        return name

    def _calculate_value_compatibility(
        self, schema_type: str, values: List[Any]
    ) -> float:
        """Calculate how well values match the expected type."""

        if not values:
            return 0.5  # Neutral score for empty values

        # Sample values (up to 10)
        sample_values = [v for v in values[:10] if v is not None and pd.notna(v)]

        if not sample_values:
            return 0.5

        # Check type compatibility
        if schema_type == "boolean":
            return self._check_boolean_compatibility(sample_values)
        elif schema_type == "number":
            return self._check_number_compatibility(sample_values)
        elif schema_type == "date":
            return self._check_date_compatibility(sample_values)
        elif schema_type == "category":
            return self._check_category_compatibility(sample_values)
        else:  # string or other
            return 0.8  # Default high compatibility for strings

    def _check_boolean_compatibility(self, values: List[Any]) -> float:
        """Check if values are boolean-like."""

        boolean_values = {
            "true",
            "false",
            "yes",
            "no",
            "y",
            "n",
            "1",
            "0",
            "t",
            "f",
            "on",
            "off",
        }

        matches = sum(1 for v in values if str(v).lower().strip() in boolean_values)

        return matches / len(values)

    def _check_number_compatibility(self, values: List[Any]) -> float:
        """Check if values are numeric."""

        matches = 0
        for value in values:
            try:
                float(str(value).replace(",", ""))
                matches += 1
            except (ValueError, TypeError):
                pass

        return matches / len(values)

    def _check_date_compatibility(self, values: List[Any]) -> float:
        """Check if values are date-like."""

        matches = 0
        for value in values:
            str_val = str(value).strip()

            # Check patterns
            for pattern in self.type_patterns["date"]:
                if re.match(pattern, str_val):
                    matches += 1
                    break
            else:
                # Try parsing
                try:
                    pd.to_datetime(str_val)
                    matches += 1
                except ParserError:
                    pass
                except ValueError:
                    pass

        return matches / len(values)

    def _check_category_compatibility(self, values: List[Any]) -> float:
        """Check if values are categorical."""

        unique_values = set(str(v).strip() for v in values)

        # Good for categories if limited unique values
        if len(unique_values) <= len(values) * 0.5:
            return 0.9
        else:
            return 0.3

    def _get_comparison_method(self, field_type: str, sample_values: List[Any]) -> str:
        """Determine best comparison method."""

        if field_type == "boolean":
            return "boolean"
        elif field_type == "number":
            return "numeric"
        elif field_type == "date":
            return "date"
        elif field_type == "category":
            # Check if values are categorical
            unique_ratio = len(set(sample_values)) / len(sample_values)
            if unique_ratio < 0.5:
                return "category"
            else:
                return "exact"
        else:
            # Check if fuzzy matching might be better
            avg_length = sum(len(str(v)) for v in sample_values) / len(sample_values)
            if avg_length > 20:  # Longer text might benefit from fuzzy
                return "fuzzy"
            else:
                return "exact"

    def _get_comparison_options(self, field_type: str, comparison_method: str) -> Dict:
        """Get default comparison options."""

        options = {}

        if comparison_method == "fuzzy":
            options["threshold"] = 85
        elif comparison_method == "numeric":
            options["tolerance"] = 0.001
            options["relative"] = False
        elif comparison_method == "exact":
            options["case_sensitive"] = False

        return options
