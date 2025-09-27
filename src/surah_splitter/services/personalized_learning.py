"""
Personalized learning service that adapts to user's voice patterns and mistakes.
"""

import json
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
from collections import defaultdict
from sklearn.cluster import KMeans
from surah_splitter.utils.app_logger import logger


class PersonalizedLearningService:
    """Adapt to individual user's voice patterns and common mistakes."""

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.model_dir = Path("models/personalized")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.user_model_file = self.model_dir / f"{user_id}_model.pkl"
        self.adaptation_data = self._init_adaptation_data()
        self.load_user_model()

    def _init_adaptation_data(self) -> Dict:
        """Initialize adaptation data structure."""
        return {
            "voice_profile": {
                "pitch_mean": None,
                "pitch_std": None,
                "speaking_rate": None,
                "pause_patterns": [],
                "energy_levels": []
            },
            "mistake_patterns": defaultdict(list),
            "pronunciation_map": {},  # Maps user's pronunciation to correct words
            "difficulty_scores": {},  # Per-word difficulty scores for this user
            "learning_curve": [],
            "preferred_pace": "balanced",
            "accent_features": {},
            "confidence_scores": {}
        }

    def load_user_model(self):
        """Load personalized model for the user."""
        if self.user_model_file.exists():
            try:
                with open(self.user_model_file, 'rb') as f:
                    self.adaptation_data = pickle.load(f)
                logger.info(f"✅ Loaded personalized model for user {self.user_id}")
            except Exception as e:
                logger.error(f"Failed to load user model: {e}")
                self.adaptation_data = self._init_adaptation_data()
        else:
            logger.info(f"Creating new personalized model for user {self.user_id}")

    def save_user_model(self):
        """Save personalized model."""
        try:
            with open(self.user_model_file, 'wb') as f:
                pickle.dump(self.adaptation_data, f)
            logger.debug(f"Saved personalized model for user {self.user_id}")
        except Exception as e:
            logger.error(f"Failed to save user model: {e}")

    def update_voice_profile(self, audio_features: Dict):
        """
        Update user's voice profile with new audio features.

        Args:
            audio_features: Dictionary containing pitch, energy, rate, etc.
        """
        profile = self.adaptation_data["voice_profile"]

        # Update pitch statistics
        if "pitch" in audio_features:
            if profile["pitch_mean"] is None:
                profile["pitch_mean"] = audio_features["pitch"]
                profile["pitch_std"] = 0
            else:
                # Running average
                alpha = 0.1  # Learning rate
                profile["pitch_mean"] = (1 - alpha) * profile["pitch_mean"] + alpha * audio_features["pitch"]

        # Update speaking rate
        if "speaking_rate" in audio_features:
            if profile["speaking_rate"] is None:
                profile["speaking_rate"] = audio_features["speaking_rate"]
            else:
                alpha = 0.1
                profile["speaking_rate"] = (1 - alpha) * profile["speaking_rate"] + alpha * audio_features["speaking_rate"]

        # Update energy levels
        if "energy" in audio_features:
            profile["energy_levels"].append(audio_features["energy"])
            if len(profile["energy_levels"]) > 100:
                profile["energy_levels"] = profile["energy_levels"][-100:]

        logger.debug(f"Updated voice profile for user {self.user_id}")

    def record_mistake(self, expected_word: str, transcribed_word: str, context: Dict):
        """
        Record a mistake for pattern analysis.

        Args:
            expected_word: The correct word
            transcribed_word: What was actually heard
            context: Additional context (position, surah, etc.)
        """
        mistake_key = f"{expected_word}→{transcribed_word}"

        # Record the mistake
        self.adaptation_data["mistake_patterns"][mistake_key].append({
            "timestamp": context.get("timestamp"),
            "position": context.get("position"),
            "surah": context.get("surah"),
            "accuracy": context.get("accuracy", 0)
        })

        # Update pronunciation map
        if transcribed_word not in self.adaptation_data["pronunciation_map"]:
            self.adaptation_data["pronunciation_map"][transcribed_word] = {}

        if expected_word not in self.adaptation_data["pronunciation_map"][transcribed_word]:
            self.adaptation_data["pronunciation_map"][transcribed_word][expected_word] = 0

        self.adaptation_data["pronunciation_map"][transcribed_word][expected_word] += 1

        # Update difficulty score for this word
        self._update_word_difficulty(expected_word, context.get("accuracy", 0))

    def _update_word_difficulty(self, word: str, accuracy: float):
        """Update personalized difficulty score for a word."""
        if word not in self.adaptation_data["difficulty_scores"]:
            self.adaptation_data["difficulty_scores"][word] = {
                "attempts": 0,
                "total_accuracy": 0,
                "recent_accuracies": [],
                "difficulty": 0.5  # Initial difficulty
            }

        scores = self.adaptation_data["difficulty_scores"][word]
        scores["attempts"] += 1
        scores["total_accuracy"] += accuracy
        scores["recent_accuracies"].append(accuracy)

        # Keep only last 10 attempts
        if len(scores["recent_accuracies"]) > 10:
            scores["recent_accuracies"] = scores["recent_accuracies"][-10:]

        # Calculate difficulty (inverse of recent average accuracy)
        recent_avg = np.mean(scores["recent_accuracies"])
        scores["difficulty"] = 1.0 - recent_avg

    def get_adjusted_similarity_threshold(self, word: str) -> float:
        """
        Get personalized similarity threshold for a word.

        Args:
            word: The word being evaluated

        Returns:
            Adjusted threshold based on user's history with this word
        """
        base_threshold = 0.7

        # Adjust based on user's difficulty with this word
        if word in self.adaptation_data["difficulty_scores"]:
            difficulty = self.adaptation_data["difficulty_scores"][word]["difficulty"]

            # Lower threshold for words user struggles with
            if difficulty > 0.7:
                return base_threshold * 0.85  # More lenient
            elif difficulty > 0.5:
                return base_threshold * 0.95
            else:
                return base_threshold

        return base_threshold

    def predict_likely_mistake(self, word: str) -> Optional[str]:
        """
        Predict what mistake the user is likely to make.

        Args:
            word: The expected word

        Returns:
            The most likely mistaken pronunciation
        """
        # Check mistake patterns
        likely_mistakes = []
        for mistake_key, occurrences in self.adaptation_data["mistake_patterns"].items():
            if mistake_key.startswith(f"{word}→"):
                transcribed = mistake_key.split("→")[1]
                likely_mistakes.append((transcribed, len(occurrences)))

        if likely_mistakes:
            # Return most common mistake
            likely_mistakes.sort(key=lambda x: x[1], reverse=True)
            return likely_mistakes[0][0]

        return None

    def get_personalized_hints(self, word: str) -> List[str]:
        """
        Get personalized hints based on user's mistake patterns.

        Args:
            word: The word user is struggling with

        Returns:
            List of personalized hints
        """
        hints = []

        # Check if user has specific patterns with this word
        if word in self.adaptation_data["difficulty_scores"]:
            difficulty = self.adaptation_data["difficulty_scores"][word]["difficulty"]

            if difficulty > 0.7:
                hints.append(f"Take your time with '{word}' - it's been challenging before")

        # Check for systematic mistakes
        likely_mistake = self.predict_likely_mistake(word)
        if likely_mistake:
            hints.append(f"Be careful not to say '{likely_mistake}'")

        # Check if user tends to rush
        if self.adaptation_data["voice_profile"]["speaking_rate"]:
            if self.adaptation_data["voice_profile"]["speaking_rate"] > 3.0:  # Words per second
                hints.append("Try slowing down slightly")

        return hints

    def adapt_transcription_result(self, transcribed: str, candidates: List[Tuple[str, float]]) -> Tuple[str, float]:
        """
        Adapt transcription result based on user's patterns.

        Args:
            transcribed: Original transcription
            candidates: List of (word, confidence) tuples

        Returns:
            Adapted (word, confidence) based on user patterns
        """
        # Check if we've seen this pronunciation before
        if transcribed in self.adaptation_data["pronunciation_map"]:
            mappings = self.adaptation_data["pronunciation_map"][transcribed]

            # Find most likely intended word
            if mappings:
                most_likely = max(mappings.items(), key=lambda x: x[1])
                intended_word = most_likely[0]
                confidence_boost = min(0.2, most_likely[1] / 10)  # Boost confidence based on frequency

                # Check if intended word is in candidates
                for word, conf in candidates:
                    if word == intended_word:
                        return intended_word, min(1.0, conf + confidence_boost)

        # Return original if no adaptation needed
        return transcribed, candidates[0][1] if candidates else 0.0

    def get_practice_recommendations(self) -> Dict:
        """
        Get personalized practice recommendations.

        Returns:
            Dictionary with recommendations
        """
        recommendations = {
            "focus_words": [],
            "suggested_pace": "balanced",
            "practice_duration": 10,  # minutes
            "tips": []
        }

        # Get words to focus on (high difficulty)
        difficult_words = []
        for word, scores in self.adaptation_data["difficulty_scores"].items():
            if scores["difficulty"] > 0.6 and scores["attempts"] >= 3:
                difficult_words.append((word, scores["difficulty"]))

        difficult_words.sort(key=lambda x: x[1], reverse=True)
        recommendations["focus_words"] = [w[0] for w in difficult_words[:10]]

        # Suggest pace based on average accuracy
        all_difficulties = [s["difficulty"] for s in self.adaptation_data["difficulty_scores"].values()]
        if all_difficulties:
            avg_difficulty = np.mean(all_difficulties)
            if avg_difficulty > 0.6:
                recommendations["suggested_pace"] = "slow"
                recommendations["tips"].append("Focus on accuracy over speed")
            elif avg_difficulty < 0.3:
                recommendations["suggested_pace"] = "fast"
                recommendations["tips"].append("Try challenging yourself with faster recitation")

        # Suggest practice duration based on learning curve
        if len(self.adaptation_data["learning_curve"]) > 5:
            recent_progress = self.adaptation_data["learning_curve"][-5:]
            if all(recent_progress[i] <= recent_progress[i-1] for i in range(1, len(recent_progress))):
                recommendations["practice_duration"] = 15
                recommendations["tips"].append("Consider longer practice sessions")

        return recommendations

    def cluster_mistake_patterns(self) -> Dict:
        """
        Cluster mistake patterns to identify systematic issues.

        Returns:
            Dictionary with clustered mistake patterns
        """
        if not self.adaptation_data["mistake_patterns"]:
            return {}

        # Prepare data for clustering
        mistakes_list = []
        mistake_labels = []

        for mistake_key, occurrences in self.adaptation_data["mistake_patterns"].items():
            if len(occurrences) >= 3:  # Only consider repeated mistakes
                mistakes_list.append(len(occurrences))
                mistake_labels.append(mistake_key)

        if len(mistakes_list) < 3:
            return {}

        # Simple clustering based on frequency
        mistake_array = np.array(mistakes_list).reshape(-1, 1)

        try:
            kmeans = KMeans(n_clusters=min(3, len(mistakes_list)), random_state=42)
            clusters = kmeans.fit_predict(mistake_array)

            clustered_mistakes = defaultdict(list)
            for i, cluster in enumerate(clusters):
                clustered_mistakes[f"pattern_{cluster}"].append({
                    "mistake": mistake_labels[i],
                    "frequency": mistakes_list[i]
                })

            return dict(clustered_mistakes)

        except Exception as e:
            logger.error(f"Failed to cluster mistakes: {e}")
            return {}

    def update_learning_curve(self, session_accuracy: float):
        """Update the user's learning curve."""
        self.adaptation_data["learning_curve"].append(session_accuracy)

        # Keep only last 50 sessions
        if len(self.adaptation_data["learning_curve"]) > 50:
            self.adaptation_data["learning_curve"] = self.adaptation_data["learning_curve"][-50:]

        # Save after updating
        self.save_user_model()

    def get_adaptation_summary(self) -> Dict:
        """Get summary of adaptation data."""
        return {
            "user_id": self.user_id,
            "total_mistakes_tracked": sum(len(v) for v in self.adaptation_data["mistake_patterns"].values()),
            "unique_mistake_patterns": len(self.adaptation_data["mistake_patterns"]),
            "words_difficulty_tracked": len(self.adaptation_data["difficulty_scores"]),
            "voice_profile_complete": self.adaptation_data["voice_profile"]["pitch_mean"] is not None,
            "sessions_tracked": len(self.adaptation_data["learning_curve"]),
            "average_difficulty": np.mean([s["difficulty"] for s in self.adaptation_data["difficulty_scores"].values()]) if self.adaptation_data["difficulty_scores"] else 0.5
        }