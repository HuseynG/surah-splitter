"""
Advanced Arabic word similarity scoring with phonetic and diacritic handling.
"""

import re
from typing import Tuple, Optional
from difflib import SequenceMatcher
import unicodedata


class ArabicSimilarityScorer:
    """Advanced Arabic text similarity scoring."""

    # Arabic diacritics (harakat)
    DIACRITICS = [
        '\u064B',  # Fathatan
        '\u064C',  # Dammatan
        '\u064D',  # Kasratan
        '\u064E',  # Fatha
        '\u064F',  # Damma
        '\u0650',  # Kasra
        '\u0651',  # Shadda
        '\u0652',  # Sukun
        '\u0653',  # Maddah
        '\u0654',  # Hamza above
        '\u0655',  # Hamza below
        '\u0656',  # Subscript alef
        '\u0640',  # Tatweel/Kashida
    ]

    # Common letter variations
    LETTER_VARIATIONS = {
        'ا': ['أ', 'إ', 'آ', 'ٱ'],  # Alif variations
        'ه': ['ة'],  # Ha variations
        'ي': ['ى', 'ئ'],  # Ya variations
        'و': ['ؤ'],  # Waw variations
    }

    # Phonetic groups (letters that sound similar)
    PHONETIC_GROUPS = [
        ['س', 'ص', 'ث'],  # S sounds
        ['ت', 'ط'],  # T sounds
        ['د', 'ض', 'ذ', 'ظ'],  # D/Th sounds
        ['ح', 'خ', 'ه'],  # H sounds
        ['ق', 'ك'],  # Q/K sounds
        ['غ', 'ع'],  # Guttural sounds
    ]

    def __init__(self):
        self._build_phonetic_map()
        self._build_variation_map()

    def _build_phonetic_map(self):
        """Build map of letters to their phonetic group."""
        self.phonetic_map = {}
        for group_idx, group in enumerate(self.PHONETIC_GROUPS):
            for letter in group:
                self.phonetic_map[letter] = group_idx

    def _build_variation_map(self):
        """Build bidirectional map of letter variations."""
        self.variation_map = {}
        for base, variations in self.LETTER_VARIATIONS.items():
            self.variation_map[base] = base
            for var in variations:
                self.variation_map[var] = base

    def remove_diacritics(self, text: str) -> str:
        """Remove all diacritics from Arabic text."""
        for diacritic in self.DIACRITICS:
            text = text.replace(diacritic, '')
        return text

    def normalize_arabic(self, text: str) -> str:
        """Normalize Arabic text by removing diacritics and standardizing letters."""
        # Remove diacritics
        text = self.remove_diacritics(text)

        # Normalize letter variations
        normalized = []
        for char in text:
            if char in self.variation_map:
                normalized.append(self.variation_map[char])
            else:
                normalized.append(char)

        return ''.join(normalized)

    def phonetic_distance(self, char1: str, char2: str) -> float:
        """Calculate phonetic distance between two Arabic characters."""
        if char1 == char2:
            return 0.0

        # Check if they're in the same phonetic group
        group1 = self.phonetic_map.get(char1)
        group2 = self.phonetic_map.get(char2)

        if group1 is not None and group1 == group2:
            return 0.3  # Same phonetic group

        return 1.0  # Different phonetic groups

    def levenshtein_distance(self, s1: str, s2: str, phonetic: bool = False) -> int:
        """Calculate Levenshtein distance with optional phonetic awareness."""
        if len(s1) < len(s2):
            return self.levenshtein_distance(s2, s1, phonetic)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                if phonetic:
                    # Use phonetic distance for substitution cost
                    cost = self.phonetic_distance(c1, c2)
                else:
                    cost = 0 if c1 == c2 else 1

                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + cost
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def calculate_similarity(
        self,
        word1: str,
        word2: str,
        consider_diacritics: bool = False,
        phonetic_matching: bool = True
    ) -> float:
        """
        Calculate similarity score between two Arabic words.

        Args:
            word1: First Arabic word
            word2: Second Arabic word
            consider_diacritics: Whether to consider diacritics in comparison
            phonetic_matching: Whether to use phonetic similarity

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Handle empty strings
        if not word1 or not word2:
            return 0.0 if (word1 or word2) else 1.0

        # Exact match with diacritics
        if word1 == word2:
            return 1.0

        # Prepare words for comparison
        if not consider_diacritics:
            clean1 = self.remove_diacritics(word1)
            clean2 = self.remove_diacritics(word2)
        else:
            clean1 = word1
            clean2 = word2

        # Exact match without diacritics
        if clean1 == clean2:
            return 0.95 if not consider_diacritics else 1.0

        # Normalize for further comparison
        norm1 = self.normalize_arabic(clean1)
        norm2 = self.normalize_arabic(clean2)

        # Match after normalization
        if norm1 == norm2:
            return 0.9

        # Calculate various similarity metrics
        scores = []

        # Sequence matching
        seq_score = SequenceMatcher(None, norm1, norm2).ratio()
        scores.append(seq_score)

        # Levenshtein-based similarity
        if phonetic_matching:
            max_len = max(len(norm1), len(norm2))
            if max_len > 0:
                lev_dist = self.levenshtein_distance(norm1, norm2, phonetic=True)
                lev_score = 1.0 - (lev_dist / max_len)
                scores.append(lev_score * 0.9)  # Weight phonetic matches slightly lower

        # Prefix/suffix matching (common in Arabic morphology)
        prefix_len = self._common_prefix_length(norm1, norm2)
        suffix_len = self._common_suffix_length(norm1, norm2)

        if prefix_len >= 3:  # Significant prefix match
            prefix_score = prefix_len / max(len(norm1), len(norm2))
            scores.append(prefix_score * 0.8)

        if suffix_len >= 2:  # Significant suffix match
            suffix_score = suffix_len / max(len(norm1), len(norm2))
            scores.append(suffix_score * 0.7)

        # Containment check (one word contains the other)
        if len(norm1) >= 3 and len(norm2) >= 3:
            if norm1 in norm2 or norm2 in norm1:
                scores.append(0.75)

        # Return weighted average of scores
        return max(scores) if scores else 0.0

    def _common_prefix_length(self, s1: str, s2: str) -> int:
        """Calculate length of common prefix."""
        for i, (c1, c2) in enumerate(zip(s1, s2)):
            if c1 != c2:
                return i
        return min(len(s1), len(s2))

    def _common_suffix_length(self, s1: str, s2: str) -> int:
        """Calculate length of common suffix."""
        return self._common_prefix_length(s1[::-1], s2[::-1])

    def get_match_confidence(self, score: float) -> Tuple[str, str]:
        """
        Get confidence level and color for a similarity score.

        Args:
            score: Similarity score (0.0 to 1.0)

        Returns:
            Tuple of (confidence_level, color)
        """
        if score >= 0.9:
            return ("perfect", "green")
        elif score >= 0.75:
            return ("good", "green")
        elif score >= 0.6:
            return ("partial", "yellow")
        elif score >= 0.4:
            return ("weak", "orange")
        else:
            return ("poor", "red")