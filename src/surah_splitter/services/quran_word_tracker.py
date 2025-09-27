"""
Quran word tracking service for intelligent word progression.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from surah_splitter.utils.app_logger import logger


class QuranWordTracker:
    """
    Tracks word progression through Quran text to prevent backwards movement
    when words are correctly identified.
    """

    def __init__(self):
        self.word_index = {}
        self.current_surah = None
        self.current_ayah = None
        self.current_position = 0
        self.confirmed_positions = set()  # Positions that have been correctly identified
        self.load_word_index()

    def load_word_index(self):
        """Load the Quran word index from JSON file."""
        try:
            index_path = Path("data/quran_metadata/quran_word_index.json")
            if index_path.exists():
                with open(index_path, 'r', encoding='utf-8') as f:
                    self.word_index = json.load(f)
                logger.info(f"✅ Loaded Quran word index with {len(self.word_index)} unique words")
            else:
                logger.warning("⚠️ Quran word index not found, using basic matching")
        except Exception as e:
            logger.error(f"❌ Failed to load Quran word index: {e}")

    def set_current_context(self, surah: int, ayah: int = None):
        """
        Set the current surah and ayah context for word tracking.
        
        Args:
            surah: Current surah number (1-114)
            ayah: Current ayah number (optional, for more precise tracking)
        """
        self.current_surah = surah
        self.current_ayah = ayah
        self.current_position = 0
        self.confirmed_positions.clear()
        logger.info(f"📍 Set context to Surah {surah}" + (f", Ayah {ayah}" if ayah else ""))

    def find_word_positions(self, word: str, surah: int, ayah: int = None) -> List[Dict]:
        """
        Find all positions of a word in the specified surah/ayah.
        
        Args:
            word: Arabic word to find
            surah: Surah number
            ayah: Ayah number (optional)
            
        Returns:
            List of position dictionaries
        """
        if word not in self.word_index:
            return []

        positions = []
        for pos_info in self.word_index[word]:
            if pos_info["surah"] == surah:
                if ayah is None or pos_info["ayah"] == ayah:
                    positions.append(pos_info)
        
        return sorted(positions, key=lambda x: x["position_wrt_surah"])

    def get_next_valid_position(self, word: str, current_pos: int) -> Optional[Dict]:
        """
        Get the next valid position for a word that hasn't been confirmed yet.
        
        Args:
            word: Arabic word
            current_pos: Current position in the surah
            
        Returns:
            Next valid position info or None
        """
        if not self.current_surah:
            return None

        positions = self.find_word_positions(word, self.current_surah, self.current_ayah)
        
        for pos_info in positions:
            pos_in_surah = pos_info["position_wrt_surah"]
            
            # Only consider positions that are:
            # 1. At or after current position
            # 2. Not already confirmed
            if pos_in_surah >= current_pos and pos_in_surah not in self.confirmed_positions:
                return pos_info
        
        return None

    def confirm_word_match(self, word: str, position: int) -> bool:
        """
        Confirm that a word has been correctly matched at a specific position.
        
        Args:
            word: Arabic word that was matched
            position: Position in surah where it was matched
            
        Returns:
            True if confirmation was successful
        """
        if position in self.confirmed_positions:
            logger.debug(f"Position {position} already confirmed")
            return False

        self.confirmed_positions.add(position)
        self.current_position = max(self.current_position, position + 1)
        
        logger.info(f"✅ Confirmed '{word}' at position {position}, advancing to {self.current_position}")
        return True

    def get_word_match_score(self, transcribed_word: str, reference_word: str, position: int) -> float:
        """
        Calculate match score considering word progression rules.
        
        Args:
            transcribed_word: Word from transcription
            reference_word: Word from reference text
            position: Position in reference text
            
        Returns:
            Match score (0.0 to 1.0), 0.0 if position should be skipped
        """
        # If this position is already confirmed, don't match it again
        if position in self.confirmed_positions:
            return 0.0

        # If this position is before our current position, heavily penalize
        if position < self.current_position:
            return 0.0

        # Calculate basic similarity
        similarity = self._calculate_word_similarity(transcribed_word, reference_word)
        
        # Bonus for positions that are at or just after current position
        position_bonus = 1.0
        if position == self.current_position:
            position_bonus = 1.2  # 20% bonus for expected next word
        elif position == self.current_position + 1:
            position_bonus = 1.1  # 10% bonus for word after next
        elif position > self.current_position + 5:
            position_bonus = 0.8  # Slight penalty for words too far ahead

        return min(1.0, similarity * position_bonus)

    def _calculate_word_similarity(self, word1: str, word2: str) -> float:
        """Calculate similarity between two Arabic words."""
        # Clean both words (remove diacritics)
        clean1 = self._clean_arabic_word(word1)
        clean2 = self._clean_arabic_word(word2)
        
        # Exact match
        if clean1 == clean2:
            return 1.0
        
        # Partial match (for different pronunciations)
        if len(clean1) >= 3 and len(clean2) >= 3:
            if clean1 in clean2 or clean2 in clean1:
                return 0.8
        
        # Character-level similarity
        max_len = max(len(clean1), len(clean2))
        if max_len == 0:
            return 0.0
        
        common_chars = sum(1 for c1, c2 in zip(clean1, clean2) if c1 == c2)
        return common_chars / max_len

    def _clean_arabic_word(self, word: str) -> str:
        """Clean Arabic word by removing diacritics."""
        import re
        # Remove diacritics and keep only Arabic letters
        cleaned = re.sub(r"[^\u0621-\u063A\u0641-\u064A]", "", word)
        return cleaned.strip()

    def get_progress_info(self) -> Dict:
        """Get current progress information."""
        return {
            "current_surah": self.current_surah,
            "current_ayah": self.current_ayah,
            "current_position": self.current_position,
            "confirmed_words": len(self.confirmed_positions),
            "confirmed_positions": sorted(list(self.confirmed_positions))
        }

    def reset_progress(self):
        """Reset tracking progress."""
        self.current_position = 0
        self.confirmed_positions.clear()
        logger.info("🔄 Reset word tracking progress")

    def can_match_word_at_position(self, word: str, position: int) -> bool:
        """
        Check if a word can be matched at a specific position.
        
        Args:
            word: Arabic word
            position: Position in reference text
            
        Returns:
            True if word can be matched at this position
        """
        # Don't allow matching at already confirmed positions
        if position in self.confirmed_positions:
            return False
            
        # Don't allow going backwards (except for very small jumps)
        if position < self.current_position - 2:
            return False
            
        return True
