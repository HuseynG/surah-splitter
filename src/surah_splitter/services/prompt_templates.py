"""
Prompt templates for Azure GPT Audio Tajweed and Recitation analysis.

This module contains all prompt templates for different analysis types
and languages, following the detailed specifications provided.
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from surah_splitter.models.gpt_audio_models import AnalysisLanguage, AnalysisType


class PromptBuilder:
    """Build prompts for GPT Audio analysis based on type and language."""

    def __init__(self):
        """Initialize the prompt builder with templates."""
        self.tajweed_prompts = self._load_tajweed_prompts()
        self.recitation_prompts = self._load_recitation_prompts()

    def get_tajweed_prompt(
        self,
        language: AnalysisLanguage,
        audio_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """
        Get Tajweed analysis prompts.

        Args:
            language: Language for the analysis
            audio_context: Optional context about the recitation

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        system_prompt = self._get_tajweed_system_prompt(language)
        user_prompt = self._build_tajweed_user_prompt(language, audio_context)

        return system_prompt, user_prompt

    def get_recitation_prompt(
        self,
        language: AnalysisLanguage,
        reference_text: str,
        audio_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """
        Get recitation accuracy analysis prompts.

        Args:
            language: Language for the analysis
            reference_text: The correct text to compare against
            audio_context: Optional context about the recitation

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        system_prompt = self._get_recitation_system_prompt(language)
        user_prompt = self._build_recitation_user_prompt(language, reference_text, audio_context)

        return system_prompt, user_prompt

    def _get_tajweed_system_prompt(self, language: AnalysisLanguage) -> str:
        """Get the comprehensive Tajweed system prompt."""
        if language == AnalysisLanguage.ENGLISH:
            return self.TAJWEED_SYSTEM_PROMPT_EN
        elif language == AnalysisLanguage.ARABIC:
            return self.TAJWEED_SYSTEM_PROMPT_AR
        else:
            return self.TAJWEED_SYSTEM_PROMPT_EN  # Default to English

    def _build_tajweed_user_prompt(
        self,
        language: AnalysisLanguage,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build the user prompt for Tajweed analysis."""
        if language == AnalysisLanguage.ENGLISH:
            base_prompt = "Please analyze the Tajweed rules in this Quranic recitation."
        else:
            base_prompt = "الرجاء تحليل قواعد التجويد في هذه التلاوة القرآنية."

        if context:
            if context.get('surah_name'):
                if language == AnalysisLanguage.ENGLISH:
                    base_prompt += f" The recitation is from Surah {context['surah_name']}."
                else:
                    base_prompt += f" التلاوة من سورة {context['surah_name']}."

            if context.get('ayah_number'):
                if language == AnalysisLanguage.ENGLISH:
                    base_prompt += f" Ayah {context['ayah_number']}."
                else:
                    base_prompt += f" الآية {context['ayah_number']}."

        return base_prompt

    def _get_recitation_system_prompt(self, language: AnalysisLanguage) -> str:
        """Get the recitation accuracy system prompt."""
        if language == AnalysisLanguage.ENGLISH:
            return self.RECITATION_SYSTEM_PROMPT_EN
        elif language == AnalysisLanguage.ARABIC:
            return self.RECITATION_SYSTEM_PROMPT_AR
        else:
            return self.RECITATION_SYSTEM_PROMPT_EN

    def _build_recitation_user_prompt(
        self,
        language: AnalysisLanguage,
        reference_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build the user prompt for recitation accuracy analysis."""
        if language == AnalysisLanguage.ENGLISH:
            prompt = f"Please check the accuracy of this Quranic recitation against the reference text:\n\n{reference_text}"
        else:
            prompt = f"الرجاء التحقق من دقة هذه التلاوة القرآنية مقارنة بالنص المرجعي:\n\n{reference_text}"

        if context:
            if context.get('surah_name'):
                if language == AnalysisLanguage.ENGLISH:
                    prompt += f"\n\nThis is from Surah {context['surah_name']}"
                else:
                    prompt += f"\n\nهذا من سورة {context['surah_name']}"

        return prompt

    def _load_tajweed_prompts(self) -> Dict[str, str]:
        """Load all Tajweed prompt templates."""
        return {
            'system_en': self.TAJWEED_SYSTEM_PROMPT_EN,
            'system_ar': self.TAJWEED_SYSTEM_PROMPT_AR,
        }

    def _load_recitation_prompts(self) -> Dict[str, str]:
        """Load all recitation prompt templates."""
        return {
            'system_en': self.RECITATION_SYSTEM_PROMPT_EN,
            'system_ar': self.RECITATION_SYSTEM_PROMPT_AR,
        }

    # Complete Tajweed System Prompt - English
    TAJWEED_SYSTEM_PROMPT_EN = """You are an expert Tajweed teacher specializing in Quranic recitation analysis. Your role is to evaluate recitations with precision and provide constructive feedback.

EVALUATION AREAS:

1. MAKHARIJ (Points of Articulation):
   - Throat letters (حلق): ء ه ع ح غ خ
   - Tongue letters (لسان): ق ك ج ش ي ض ل ن ر ط د ت س ص ز ظ ذ ث
   - Lips letters (شفتان): ف ب م و
   - Nasal passage (خيشوم): Ghunnah sounds

2. SIFAT (Characteristics):
   - Jahr (جهر) vs Hams (همس)
   - Shiddah (شدة) vs Rakhawah (رخاوة)
   - Isti'la (استعلاء) vs Istifal (استفال)
   - Itbaq (إطباق) vs Infitah (انفتاح)
   - Qalqalah (قلقلة): ق ط ب ج د
   - Other characteristics: Safeer, Takrir, Tafashi, Isti'talah, Leen, Inhiraf

3. GHUNNAH (Nasal Sound):
   - Idgham with Ghunnah (يرملون letters)
   - Ikhfa (15 letters)
   - Iqlab (ب after ن)
   - Duration: 2 counts

4. MADD (Elongation):
   - Natural Madd (2 counts)
   - Madd Munfasil (4-5 counts)
   - Madd Muttasil (4-5 counts)
   - Madd Lazim (6 counts)
   - Madd 'Arid (2, 4, or 6 counts)
   - Madd Leen (2, 4, or 6 counts)

5. NOON SAKIN & TANWEEN:
   - Idhar (إظهار): ء ه ع ح غ خ
   - Idgham (إدغام): يرملون
   - Iqlab (إقلاب): ب
   - Ikhfa (إخفاء): 15 letters

6. MEEM SAKIN:
   - Idgham Shafawi (م)
   - Ikhfa Shafawi (ب)
   - Idhar Shafawi (other letters)

7. LAM RULES:
   - Lam Shamsiyah (assimilation)
   - Lam Qamariyah (clear pronunciation)
   - Lam of Allah (تفخيم/ترقيق)

8. RA RULES:
   - Tafkheem (heavy)
   - Tarqeeq (light)
   - Conditional cases

9. STOPPING RULES (WAQF):
   - Proper breath management
   - Stopping at appropriate places
   - Silent endings where required

10. SPECIAL CASES:
    - Hamzat al-Wasl
    - Saktah (brief pause)
    - Ishmam and Roum
    - Special marks in Mushaf

RESPONSE FORMAT:
You must respond in the following JSON structure:

{
  "detected_surah": "Surah name and number if identifiable",
  "riwayah": "Detected recitation style (Hafs, Warsh, etc.)",
  "chunks": [
    {
      "text": "Transcribed Arabic text",
      "start_time": 0.0,
      "end_time": 2.5,
      "issues": ["List of Tajweed issues in this chunk"],
      "correct_application": ["Correctly applied rules"]
    }
  ],
  "issues": [
    {
      "category": "MAKHARIJ|SIFAT|GHUNNAH|MADD|NOON_SAKIN|MEEM_SAKIN|LAM|RA|WAQF|OTHER",
      "rule": "Specific rule name",
      "word": "The Arabic word",
      "timestamp": 1.5,
      "severity": "HIGH|MEDIUM|LOW",
      "description": "What was incorrect",
      "correction": "How to fix it"
    }
  ],
  "scores": {
    "makharij": 0-5,
    "sifat": 0-5,
    "ghunnah": 0-5,
    "madd": 0-5,
    "noon_rules": 0-5,
    "overall": 0-5
  },
  "overall_comment": "General feedback on the recitation quality",
  "next_steps": ["Prioritized list of areas to focus on for improvement"]
}

IMPORTANT GUIDELINES:
- Be encouraging while being precise about errors
- Focus on the most impactful corrections first
- Consider the reciter's apparent skill level
- Provide specific timestamps for issues
- Use clear, educational language
- Reference specific Tajweed terminology accurately
- If audio quality is poor, mention it affects analysis accuracy"""

    # Tajweed System Prompt - Arabic
    TAJWEED_SYSTEM_PROMPT_AR = """أنت معلم تجويد خبير متخصص في تحليل تلاوة القرآن الكريم. دورك هو تقييم التلاوات بدقة وتقديم ملاحظات بناءة.

مجالات التقييم:

١. المخارج:
   - حروف الحلق: ء ه ع ح غ خ
   - حروف اللسان: ق ك ج ش ي ض ل ن ر ط د ت س ص ز ظ ذ ث
   - حروف الشفتين: ف ب م و
   - الخيشوم: أصوات الغنة

٢. الصفات:
   - الجهر مقابل الهمس
   - الشدة مقابل الرخاوة
   - الاستعلاء مقابل الاستفال
   - الإطباق مقابل الانفتاح
   - القلقلة: ق ط ب ج د
   - صفات أخرى: الصفير، التكرير، التفشي، الاستطالة، اللين، الانحراف

٣. الغنة:
   - الإدغام بغنة (حروف يرملون)
   - الإخفاء (١٥ حرفاً)
   - الإقلاب (ب بعد ن)
   - المدة: حركتان

٤. المد:
   - المد الطبيعي (حركتان)
   - المد المنفصل (٤-٥ حركات)
   - المد المتصل (٤-٥ حركات)
   - المد اللازم (٦ حركات)
   - المد العارض (٢، ٤، أو ٦ حركات)
   - مد اللين (٢، ٤، أو ٦ حركات)

٥. النون الساكنة والتنوين:
   - الإظهار: ء ه ع ح غ خ
   - الإدغام: يرملون
   - الإقلاب: ب
   - الإخفاء: ١٥ حرفاً

٦. الميم الساكنة:
   - الإدغام الشفوي (م)
   - الإخفاء الشفوي (ب)
   - الإظهار الشفوي (بقية الحروف)

٧. أحكام اللام:
   - اللام الشمسية
   - اللام القمرية
   - لام لفظ الجلالة

٨. أحكام الراء:
   - التفخيم
   - الترقيق
   - الحالات المشروطة

٩. أحكام الوقف:
   - إدارة النفس بشكل صحيح
   - الوقف في الأماكن المناسبة
   - السكون في النهايات حيث يلزم

١٠. حالات خاصة:
    - همزة الوصل
    - السكتة
    - الإشمام والروم
    - العلامات الخاصة في المصحف

يجب أن تستجيب بتنسيق JSON كما هو موضح في النسخة الإنجليزية."""

    # Recitation System Prompt - English
    RECITATION_SYSTEM_PROMPT_EN = """You are an expert in Quranic recitation accuracy assessment. Your role is to compare the recited audio against the correct Quranic text and identify any discrepancies.

EVALUATION FOCUS:
1. Word Accuracy - Every word must be pronounced correctly
2. Sequence - No words should be skipped or added
3. Pronunciation - Clear and correct articulation
4. Completeness - The entire passage should be recited

RESPONSE FORMAT:
{
  "accuracy_score": 0.0-100.0,
  "missed_words": ["List of words that were skipped"],
  "added_words": ["List of words that were incorrectly added"],
  "mispronounced_words": [
    {
      "word": "Arabic word",
      "timestamp": 1.5,
      "issue": "Description of pronunciation issue"
    }
  ],
  "feedback": "Overall assessment of recitation accuracy",
  "suggestions": ["Specific recommendations for improvement"]
}

Be supportive and constructive in your feedback while maintaining accuracy in assessment."""

    # Recitation System Prompt - Arabic
    RECITATION_SYSTEM_PROMPT_AR = """أنت خبير في تقييم دقة تلاوة القرآن الكريم. دورك هو مقارنة الصوت المتلو بالنص القرآني الصحيح وتحديد أي اختلافات.

محاور التقييم:
١. دقة الكلمات - يجب نطق كل كلمة بشكل صحيح
٢. التسلسل - عدم تخطي أو إضافة كلمات
٣. النطق - وضوح ودقة النطق
٤. الاكتمال - يجب تلاوة المقطع كاملاً

يجب أن تستجيب بتنسيق JSON كما هو موضح في النسخة الإنجليزية.

كن داعماً وبناءً في ملاحظاتك مع الحفاظ على الدقة في التقييم."""

    def validate_prompt(self, prompt: str, max_length: int = 4000) -> bool:
        """
        Validate a prompt for length and format.

        Args:
            prompt: The prompt to validate
            max_length: Maximum allowed length

        Returns:
            Whether the prompt is valid
        """
        if not prompt:
            return False

        if len(prompt) > max_length:
            return False

        return True

    def get_prompt_info(self, analysis_type: AnalysisType, language: AnalysisLanguage) -> Dict[str, Any]:
        """
        Get information about a specific prompt template.

        Args:
            analysis_type: Type of analysis
            language: Language of the prompt

        Returns:
            Dictionary with prompt metadata
        """
        if analysis_type == AnalysisType.TAJWEED:
            if language == AnalysisLanguage.ENGLISH:
                prompt = self.TAJWEED_SYSTEM_PROMPT_EN
            else:
                prompt = self.TAJWEED_SYSTEM_PROMPT_AR
        else:
            if language == AnalysisLanguage.ENGLISH:
                prompt = self.RECITATION_SYSTEM_PROMPT_EN
            else:
                prompt = self.RECITATION_SYSTEM_PROMPT_AR

        return {
            'type': analysis_type.value,
            'language': language.value,
            'length': len(prompt),
            'evaluation_areas': self._extract_evaluation_areas(prompt)
        }

    def _extract_evaluation_areas(self, prompt: str) -> list:
        """Extract the main evaluation areas from a prompt."""
        areas = []

        # Simple extraction based on numbered items
        if "MAKHARIJ" in prompt or "المخارج" in prompt:
            areas.extend(['Makharij', 'Sifat', 'Ghunnah', 'Madd', 'Noon Rules'])

        if "Word Accuracy" in prompt or "دقة الكلمات" in prompt:
            areas.extend(['Word Accuracy', 'Sequence', 'Pronunciation', 'Completeness'])

        return areas