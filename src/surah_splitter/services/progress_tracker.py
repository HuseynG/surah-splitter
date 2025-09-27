"""
User progress tracking and statistics service.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict
import numpy as np
from surah_splitter.utils.app_logger import logger


class ProgressTracker:
    """Track and analyze user progress in Quran recitation."""

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.data_dir = Path("data/user_progress")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.user_file = self.data_dir / f"{user_id}_progress.json"
        self.session_data = []
        self.load_user_data()

    def load_user_data(self):
        """Load user progress data from file."""
        if self.user_file.exists():
            try:
                with open(self.user_file, 'r') as f:
                    self.user_data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load user data: {e}")
                self.user_data = self._init_user_data()
        else:
            self.user_data = self._init_user_data()

    def _init_user_data(self) -> Dict:
        """Initialize empty user data structure."""
        return {
            "user_id": self.user_id,
            "created_at": datetime.now().isoformat(),
            "sessions": [],
            "surah_progress": {},
            "statistics": {
                "total_sessions": 0,
                "total_minutes": 0,
                "total_words": 0,
                "average_accuracy": 0,
                "best_accuracy": 0,
                "streak_days": 0,
                "last_session": None
            },
            "achievements": [],
            "word_difficulties": {},
            "common_mistakes": {}
        }

    def start_session(self, surah_number: int, surah_name: str):
        """Start a new practice session."""
        self.current_session = {
            "session_id": datetime.now().isoformat(),
            "started_at": datetime.now().isoformat(),
            "surah_number": surah_number,
            "surah_name": surah_name,
            "word_accuracies": [],
            "mistakes": [],
            "duration_seconds": 0,
            "overall_accuracy": 0,
            "words_completed": 0
        }
        self.session_start_time = datetime.now()
        logger.info(f"📊 Started tracking session for {surah_name}")

    def record_word_feedback(self, feedback: Dict):
        """Record feedback for a word."""
        if not hasattr(self, 'current_session'):
            return

        word_record = {
            "word": feedback.get("reference_word", ""),
            "transcribed": feedback.get("transcribed_word", ""),
            "accuracy": feedback.get("alignment_score", 0),
            "position": feedback.get("position", 0),
            "timestamp": datetime.now().isoformat()
        }

        self.current_session["word_accuracies"].append(word_record)

        # Track mistakes
        if word_record["accuracy"] < 0.7:
            mistake = {
                "expected": word_record["word"],
                "heard": word_record["transcribed"],
                "accuracy": word_record["accuracy"]
            }
            self.current_session["mistakes"].append(mistake)

            # Update common mistakes
            mistake_key = f"{word_record['word']}→{word_record['transcribed']}"
            if mistake_key not in self.user_data["common_mistakes"]:
                self.user_data["common_mistakes"][mistake_key] = 0
            self.user_data["common_mistakes"][mistake_key] += 1

        # Update word difficulties
        word = word_record["word"]
        if word not in self.user_data["word_difficulties"]:
            self.user_data["word_difficulties"][word] = []
        self.user_data["word_difficulties"][word].append(word_record["accuracy"])

    def end_session(self):
        """End current session and save statistics."""
        if not hasattr(self, 'current_session'):
            return

        # Calculate session statistics
        duration = (datetime.now() - self.session_start_time).total_seconds()
        self.current_session["duration_seconds"] = duration
        self.current_session["ended_at"] = datetime.now().isoformat()

        # Calculate overall accuracy
        if self.current_session["word_accuracies"]:
            accuracies = [w["accuracy"] for w in self.current_session["word_accuracies"]]
            self.current_session["overall_accuracy"] = np.mean(accuracies)
            self.current_session["words_completed"] = len(accuracies)

        # Update user statistics
        self._update_statistics()

        # Add session to history
        self.user_data["sessions"].append(self.current_session)

        # Keep only last 100 sessions
        if len(self.user_data["sessions"]) > 100:
            self.user_data["sessions"] = self.user_data["sessions"][-100:]

        # Save to file
        self.save_user_data()

        logger.info(f"📊 Session ended: {self.current_session['words_completed']} words, "
                   f"{self.current_session['overall_accuracy']:.1%} accuracy")

        return self.get_session_summary()

    def _update_statistics(self):
        """Update overall user statistics."""
        stats = self.user_data["statistics"]

        # Update totals
        stats["total_sessions"] += 1
        stats["total_minutes"] += self.current_session["duration_seconds"] / 60
        stats["total_words"] += self.current_session["words_completed"]

        # Update accuracy
        all_accuracies = []
        for session in self.user_data["sessions"]:
            if session.get("overall_accuracy"):
                all_accuracies.append(session["overall_accuracy"])
        if self.current_session.get("overall_accuracy"):
            all_accuracies.append(self.current_session["overall_accuracy"])

        if all_accuracies:
            stats["average_accuracy"] = np.mean(all_accuracies)
            stats["best_accuracy"] = max(all_accuracies)

        # Update streak
        stats["last_session"] = datetime.now().isoformat()
        self._update_streak()

        # Check for achievements
        self._check_achievements()

        # Update surah progress
        surah_num = str(self.current_session["surah_number"])
        if surah_num not in self.user_data["surah_progress"]:
            self.user_data["surah_progress"][surah_num] = {
                "practice_count": 0,
                "best_accuracy": 0,
                "average_accuracy": 0,
                "last_practiced": None
            }

        surah_prog = self.user_data["surah_progress"][surah_num]
        surah_prog["practice_count"] += 1
        surah_prog["last_practiced"] = datetime.now().isoformat()

        # Update surah accuracy
        surah_sessions = [s for s in self.user_data["sessions"]
                         if s["surah_number"] == self.current_session["surah_number"]]
        if surah_sessions:
            surah_accuracies = [s["overall_accuracy"] for s in surah_sessions
                               if s.get("overall_accuracy")]
            if surah_accuracies:
                surah_prog["average_accuracy"] = np.mean(surah_accuracies)
                surah_prog["best_accuracy"] = max(surah_accuracies)

    def _update_streak(self):
        """Update practice streak."""
        if not self.user_data["sessions"]:
            self.user_data["statistics"]["streak_days"] = 1
            return

        # Get unique practice days
        practice_days = set()
        for session in self.user_data["sessions"]:
            day = session["started_at"][:10]  # YYYY-MM-DD
            practice_days.add(day)

        # Add today
        practice_days.add(datetime.now().date().isoformat())

        # Check for consecutive days
        sorted_days = sorted(practice_days)
        streak = 1
        for i in range(len(sorted_days) - 1, 0, -1):
            current = datetime.fromisoformat(sorted_days[i]).date()
            previous = datetime.fromisoformat(sorted_days[i-1]).date()

            if (current - previous).days == 1:
                streak += 1
            else:
                break

        self.user_data["statistics"]["streak_days"] = streak

    def _check_achievements(self):
        """Check and award achievements."""
        achievements = self.user_data["achievements"]
        stats = self.user_data["statistics"]

        # Define achievement criteria
        achievement_checks = [
            ("first_session", "First Steps", stats["total_sessions"] >= 1),
            ("10_sessions", "Regular Practitioner", stats["total_sessions"] >= 10),
            ("100_words", "Century", stats["total_words"] >= 100),
            ("1000_words", "Word Master", stats["total_words"] >= 1000),
            ("90_accuracy", "Precision Reader", self.current_session.get("overall_accuracy", 0) >= 0.9),
            ("perfect_session", "Perfect Recitation", self.current_session.get("overall_accuracy", 0) >= 0.98),
            ("7_day_streak", "Week Warrior", stats["streak_days"] >= 7),
            ("30_day_streak", "Monthly Master", stats["streak_days"] >= 30),
            ("hour_practiced", "Dedicated Learner", stats["total_minutes"] >= 60),
        ]

        for achievement_id, name, condition in achievement_checks:
            if condition and achievement_id not in [a["id"] for a in achievements]:
                new_achievement = {
                    "id": achievement_id,
                    "name": name,
                    "earned_at": datetime.now().isoformat()
                }
                achievements.append(new_achievement)
                logger.info(f"🏆 Achievement unlocked: {name}")

    def get_session_summary(self) -> Dict:
        """Get summary of current session."""
        if not hasattr(self, 'current_session'):
            return {}

        return {
            "duration_minutes": self.current_session["duration_seconds"] / 60,
            "words_completed": self.current_session["words_completed"],
            "accuracy": self.current_session["overall_accuracy"],
            "mistakes_count": len(self.current_session["mistakes"]),
            "top_mistakes": self.current_session["mistakes"][:5] if self.current_session["mistakes"] else []
        }

    def get_progress_stats(self) -> Dict:
        """Get overall progress statistics."""
        return {
            "statistics": self.user_data["statistics"],
            "recent_sessions": self.user_data["sessions"][-5:],
            "achievements": self.user_data["achievements"],
            "improvement_trend": self._calculate_improvement_trend(),
            "difficult_words": self._get_difficult_words(),
            "mastered_surahs": self._get_mastered_surahs()
        }

    def _calculate_improvement_trend(self) -> Dict:
        """Calculate improvement trend over time."""
        if len(self.user_data["sessions"]) < 2:
            return {"trend": "neutral", "change": 0}

        recent_sessions = self.user_data["sessions"][-10:]
        if len(recent_sessions) < 2:
            return {"trend": "neutral", "change": 0}

        # Compare first half vs second half
        mid_point = len(recent_sessions) // 2
        first_half = recent_sessions[:mid_point]
        second_half = recent_sessions[mid_point:]

        first_avg = np.mean([s["overall_accuracy"] for s in first_half
                            if s.get("overall_accuracy")])
        second_avg = np.mean([s["overall_accuracy"] for s in second_half
                             if s.get("overall_accuracy")])

        change = second_avg - first_avg

        if change > 0.05:
            trend = "improving"
        elif change < -0.05:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "change": change,
            "message": self._get_trend_message(trend, change)
        }

    def _get_trend_message(self, trend: str, change: float) -> str:
        """Get encouraging message based on trend."""
        if trend == "improving":
            return f"Great progress! Your accuracy improved by {change:.1%}"
        elif trend == "stable":
            return "Consistent performance! Keep practicing"
        else:
            return "Don't give up! Focus on difficult words"

    def _get_difficult_words(self, limit: int = 10) -> List[Dict]:
        """Get words that need more practice."""
        difficult = []
        for word, accuracies in self.user_data["word_difficulties"].items():
            if len(accuracies) >= 3:  # Only consider words practiced at least 3 times
                avg_accuracy = np.mean(accuracies[-5:])  # Last 5 attempts
                if avg_accuracy < 0.7:
                    difficult.append({
                        "word": word,
                        "average_accuracy": avg_accuracy,
                        "attempts": len(accuracies)
                    })

        return sorted(difficult, key=lambda x: x["average_accuracy"])[:limit]

    def _get_mastered_surahs(self) -> List[Dict]:
        """Get surahs with high proficiency."""
        mastered = []
        for surah_num, progress in self.user_data["surah_progress"].items():
            if progress["best_accuracy"] >= 0.9 and progress["practice_count"] >= 3:
                mastered.append({
                    "surah_number": int(surah_num),
                    "best_accuracy": progress["best_accuracy"],
                    "practice_count": progress["practice_count"]
                })

        return sorted(mastered, key=lambda x: x["best_accuracy"], reverse=True)

    def save_user_data(self):
        """Save user data to file."""
        try:
            with open(self.user_file, 'w') as f:
                json.dump(self.user_data, f, indent=2)
            logger.debug(f"Saved progress for user {self.user_id}")
        except Exception as e:
            logger.error(f"Failed to save user progress: {e}")

    def export_progress_report(self) -> str:
        """Export detailed progress report."""
        stats = self.user_data["statistics"]
        report = f"""
# Quran Recitation Progress Report
**User:** {self.user_id}
**Date:** {datetime.now().strftime('%Y-%m-%d')}

## Overall Statistics
- Total Sessions: {stats['total_sessions']}
- Total Practice Time: {stats['total_minutes']:.1f} minutes
- Total Words: {stats['total_words']}
- Average Accuracy: {stats['average_accuracy']:.1%}
- Best Accuracy: {stats['best_accuracy']:.1%}
- Current Streak: {stats['streak_days']} days

## Achievements Earned
"""
        for achievement in self.user_data["achievements"]:
            report += f"- 🏆 {achievement['name']}\n"

        report += "\n## Mastered Surahs\n"
        for surah in self._get_mastered_surahs():
            report += f"- Surah {surah['surah_number']}: {surah['best_accuracy']:.1%} accuracy\n"

        report += "\n## Areas for Improvement\n"
        for word_info in self._get_difficult_words(5):
            report += f"- {word_info['word']}: {word_info['average_accuracy']:.1%} avg accuracy\n"

        return report