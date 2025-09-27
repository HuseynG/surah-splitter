"""
Tajweed rules analyzer for Quran recitation.
"""

from typing import Dict, List, Optional, Tuple
import re
from surah_splitter.utils.app_logger import logger


class TajweedAnalyzer:
    """Analyze Quran recitation for Tajweed rules compliance."""

    # Tajweed letters categories
    QALQALAH_LETTERS = ['ق', 'ط', 'ب', 'ج', 'د']
    GHUNNAH_LETTERS = ['ن', 'م']
    ISTI_ALA_LETTERS = ['خ', 'ص', 'ض', 'غ', 'ط', 'ق', 'ظ']  # Heavy letters
    THROAT_LETTERS = ['ء', 'ه', 'ع', 'ح', 'غ', 'خ']

    # Madd letters
    MADD_LETTERS = {
        'ا': 'alif',
        'و': 'waw',
        'ي': 'ya'
    }

    # Diacritics
    DIACRITICS = {
        '\u064B': 'fathatan',
        '\u064C': 'dammatan',
        '\u064D': 'kasratan',
        '\u064E': 'fatha',
        '\u064F': 'damma',
        '\u0650': 'kasra',
        '\u0651': 'shadda',
        '\u0652': 'sukun',
        '\u0670': 'dagger_alif'
    }

    def __init__(self):
        self.rules_checked = []
        self.violations = []

    def analyze_word(self, word: str, audio_features: Optional[Dict] = None) -> Dict:
        """
        Analyze a word for Tajweed rules.

        Args:
            word: Arabic word with diacritics
            audio_features: Optional audio analysis features

        Returns:
            Analysis results with rules and recommendations
        """
        results = {
            "word": word,
            "rules": [],
            "violations": [],
            "recommendations": [],
            "score": 1.0
        }

        # Check various Tajweed rules
        self._check_qalqalah(word, results)
        self._check_ghunnah(word, results)
        self._check_madd(word, results)
        self._check_idgham(word, results)
        self._check_ikhfa(word, results)
        self._check_iqlab(word, results)

        # Calculate compliance score
        if results["rules"]:
            violations_count = len(results["violations"])
            rules_count = len(results["rules"])
            results["score"] = max(0, 1 - (violations_count / rules_count))

        return results

    def _check_qalqalah(self, word: str, results: Dict):
        """Check for Qalqalah (echo/vibration) rules."""
        for i, char in enumerate(word):
            if char in self.QALQALAH_LETTERS:
                # Check if letter has sukun or is at end of word
                has_sukun = i + 1 < len(word) and word[i + 1] == '\u0652'
                is_end = i == len(word) - 1 or (
                    i == len(word) - 2 and word[-1] in self.DIACRITICS
                )

                if has_sukun or is_end:
                    rule = {
                        "type": "qalqalah",
                        "letter": char,
                        "position": i,
                        "strength": "major" if is_end else "minor",
                        "description": f"Apply Qalqalah on '{char}'"
                    }
                    results["rules"].append(rule)

                    # Add recommendation
                    if is_end:
                        results["recommendations"].append(
                            f"Strong echo on '{char}' at word end"
                        )
                    else:
                        results["recommendations"].append(
                            f"Light bounce on '{char}' with sukun"
                        )

    def _check_ghunnah(self, word: str, results: Dict):
        """Check for Ghunnah (nasalization) rules."""
        for i, char in enumerate(word):
            if char in self.GHUNNAH_LETTERS:
                # Check for shadda (doubling)
                has_shadda = i + 1 < len(word) and word[i + 1] == '\u0651'

                if has_shadda:
                    rule = {
                        "type": "ghunnah",
                        "letter": char,
                        "position": i,
                        "duration": "2_counts",
                        "description": f"Ghunnah with shadda on '{char}'"
                    }
                    results["rules"].append(rule)
                    results["recommendations"].append(
                        f"Hold nasal sound for 2 counts on '{char}'"
                    )

    def _check_madd(self, word: str, results: Dict):
        """Check for Madd (elongation) rules."""
        for i, char in enumerate(word):
            if char in self.MADD_LETTERS:
                # Check what comes before the madd letter
                if i > 0:
                    prev_char = word[i - 1]

                    # Natural madd (2 counts)
                    if prev_char == '\u064E' and char == 'ا':  # Fatha + Alif
                        self._add_madd_rule(results, char, i, "natural", 2)
                    elif prev_char == '\u064F' and char == 'و':  # Damma + Waw
                        self._add_madd_rule(results, char, i, "natural", 2)
                    elif prev_char == '\u0650' and char == 'ي':  # Kasra + Ya
                        self._add_madd_rule(results, char, i, "natural", 2)

                # Check for hamza after (madd munfasil/muttasil)
                if i + 1 < len(word) and word[i + 1] == 'ء':
                    self._add_madd_rule(results, char, i, "muttasil", 4)

    def _add_madd_rule(self, results: Dict, letter: str, position: int,
                       madd_type: str, counts: int):
        """Add a madd rule to results."""
        rule = {
            "type": "madd",
            "subtype": madd_type,
            "letter": letter,
            "position": position,
            "duration": f"{counts}_counts",
            "description": f"Madd {madd_type} on '{letter}' ({counts} counts)"
        }
        results["rules"].append(rule)
        results["recommendations"].append(
            f"Elongate '{letter}' for {counts} counts"
        )

    def _check_idgham(self, word: str, results: Dict):
        """Check for Idgham (merging) rules."""
        # This requires checking across word boundaries
        idgham_letters = ['ي', 'ر', 'م', 'ل', 'و', 'ن']

        # Check if word ends with noon sakin
        if len(word) >= 2 and word[-2] == 'ن' and word[-1] == '\u0652':
            rule = {
                "type": "idgham_candidate",
                "description": "Noon sakin at end - check next word for Idgham"
            }
            results["rules"].append(rule)

    def _check_ikhfa(self, word: str, results: Dict):
        """Check for Ikhfa (concealment) rules."""
        ikhfa_letters = [
            'ت', 'ث', 'ج', 'د', 'ذ', 'ز', 'س', 'ش',
            'ص', 'ض', 'ط', 'ظ', 'ف', 'ق', 'ك'
        ]

        for i, char in enumerate(word[:-1]):
            if char == 'ن' and i + 1 < len(word):
                next_char = word[i + 1]
                if next_char in ikhfa_letters:
                    rule = {
                        "type": "ikhfa",
                        "position": i,
                        "description": f"Hide noon before '{next_char}'"
                    }
                    results["rules"].append(rule)
                    results["recommendations"].append(
                        f"Conceal the noon sound before '{next_char}'"
                    )

    def _check_iqlab(self, word: str, results: Dict):
        """Check for Iqlab (conversion) rules."""
        for i, char in enumerate(word[:-1]):
            # Noon sakin or tanween followed by ba
            if char == 'ن' and i + 1 < len(word) and word[i + 1] == 'ب':
                rule = {
                    "type": "iqlab",
                    "position": i,
                    "description": "Convert noon to meem before ba"
                }
                results["rules"].append(rule)
                results["recommendations"].append(
                    "Change noon sound to meem before 'ب'"
                )

    def analyze_verse(self, verse: str, word_timings: Optional[List[Dict]] = None) -> Dict:
        """
        Analyze a complete verse for Tajweed rules.

        Args:
            verse: Complete Arabic verse with diacritics
            word_timings: Optional timing information for each word

        Returns:
            Comprehensive Tajweed analysis
        """
        words = verse.split()
        verse_analysis = {
            "verse": verse,
            "word_count": len(words),
            "total_rules": 0,
            "total_violations": 0,
            "word_analyses": [],
            "overall_score": 0
        }

        scores = []
        for i, word in enumerate(words):
            word_analysis = self.analyze_word(word)

            # Check cross-word rules (like idgham between words)
            if i < len(words) - 1:
                self._check_cross_word_rules(word, words[i + 1], word_analysis)

            verse_analysis["word_analyses"].append(word_analysis)
            verse_analysis["total_rules"] += len(word_analysis["rules"])
            verse_analysis["total_violations"] += len(word_analysis["violations"])
            scores.append(word_analysis["score"])

        # Calculate overall score
        verse_analysis["overall_score"] = sum(scores) / len(scores) if scores else 0

        return verse_analysis

    def _check_cross_word_rules(self, current_word: str, next_word: str, analysis: Dict):
        """Check Tajweed rules that apply across word boundaries."""
        # Check for idgham between words
        if current_word.endswith('ن\u0652') or current_word.endswith('ً'):  # Noon sakin or tanween
            if next_word and next_word[0] in ['ي', 'ر', 'م', 'ل', 'و', 'ن']:
                analysis["rules"].append({
                    "type": "idgham",
                    "description": f"Merge noon into '{next_word[0]}' of next word"
                })

    def get_tajweed_feedback(self, analysis: Dict) -> str:
        """Generate human-readable Tajweed feedback."""
        if not analysis["rules"]:
            return "No specific Tajweed rules detected in this word."

        feedback = []
        for rule in analysis["rules"]:
            if rule["type"] == "qalqalah":
                feedback.append(f"• {rule['strength'].capitalize()} Qalqalah on {rule['letter']}")
            elif rule["type"] == "ghunnah":
                feedback.append(f"• Ghunnah (2 counts) on {rule['letter']}")
            elif rule["type"] == "madd":
                feedback.append(f"• {rule['description']}")
            elif rule["type"] == "ikhfa":
                feedback.append(f"• {rule['description']}")
            elif rule["type"] == "iqlab":
                feedback.append(f"• {rule['description']}")
            elif rule["type"] == "idgham":
                feedback.append(f"• {rule['description']}")

        return "\n".join(feedback)