"""
Neural Network Content Classifier
Автоматическая классификация контента с помощью нейросети
"""

import logging
from typing import Dict, List, Tuple
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch

logger = logging.getLogger(__name__)

class ContentClassifier:
    def __init__(self):
        """Initialize the classifier with pre-trained model"""
        self.categories = {
            "🚀 НОВЫЙ РЕЛИЗ": [
                "релиз новой модели", "запуск продукта", "выпуск обновления", 
                "представлена модель", "доступна новая версия", "анонс релиза",
                "launch", "release", "new model", "product launch", "update available"
            ],
            "✨ ПРЕДСТАВЛЕНА НОВАЯ МОДЕЛЬ": [
                "новая языковая модель", "представлена модель", "модель ИИ",
                "нейросеть", "AI model", "neural network", "GPT", "Claude", "Gemini"
            ],
            "🎉 ЗАПУСК ПРОДУКТА": [
                "запуск продукта", "новый продукт", "стартап", "платформа",
                "product launch", "new product", "startup", "platform launch"
            ],
            "🔥 ДОСТУПНО ОБНОВЛЕНИЕ": [
                "обновление", "апдейт", "новая версия", "улучшения",
                "update", "upgrade", "new version", "improvements"
            ],
            "📄 НОВОЕ ИССЛЕДОВАНИЕ": [
                "исследование", "научная работа", "эксперимент", "изучение",
                "research", "study", "experiment", "scientific paper"
            ],
            "🔬 ОПУБЛИКОВАНА СТАТЬЯ": [
                "статья", "публикация", "научная статья", "доклад",
                "article", "publication", "paper", "report"
            ],
            "📊 АНАЛИЗ | РЕЗУЛЬТАТЫ": [
                "анализ", "результаты", "данные", "статистика", "отчет",
                "analysis", "results", "data", "statistics", "findings"
            ],
            "🧠 МНЕНИЕ ФАУНДЕРА": [
                "основатель", "CEO", "фаундер", "мнение руководителя",
                "founder", "CEO opinion", "executive statement"
            ],
            "💬 ПРЯМАЯ РЕЧЬ": [
                "заявление", "комментарий", "интервью", "высказывание",
                "statement", "comment", "interview", "quote"
            ],
            "💡 ИНСАЙТ ОТ ЭКСПЕРТА": [
                "эксперт", "специалист", "инсайт", "экспертное мнение",
                "expert", "specialist", "insight", "expert opinion"
            ],
            "📈 НОВОСТИ КОМПАНИИ": [
                "компания", "корпорация", "бизнес", "организация",
                "company", "corporation", "business", "organization"
            ],
            "💰 ИНВЕСТИЦИИ": [
                "инвестиции", "финансирование", "раунд", "венчурные",
                "investment", "funding", "round", "venture capital"
            ],
            "🤝 КАДРОВЫЕ ИЗМЕНЕНИЯ": [
                "назначение", "увольнение", "новый сотрудник", "кадры",
                "appointment", "hiring", "new employee", "staff changes"
            ],
            "⚡️ МОЛНИЯ": [
                "срочно", "экстренно", "важная новость", "молния",
                "breaking", "urgent", "important news", "alert"
            ],
            "⚠️ ВАЖНОЕ СОБЫТИЕ": [
                "важное событие", "значимое", "критически важно",
                "important event", "significant", "critical"
            ]
        }
        
        self.classifier = None
        self.model_name = "facebook/bart-large-mnli"
        self._load_model()
    
    def _load_model(self):
        """Load the pre-trained model for zero-shot classification"""
        try:
            logger.info("Loading zero-shot classification model...")
            self.classifier = pipeline(
                "zero-shot-classification",
                model=self.model_name,
                device=0 if torch.cuda.is_available() else -1
            )
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.classifier = None
    
    def _prepare_candidate_labels(self) -> List[str]:
        """Prepare candidate labels for classification"""
        return list(self.categories.keys())
    
    def _enhance_text_with_keywords(self, text: str) -> str:
        """Enhance text with relevant keywords for better classification"""
        enhanced_text = text.lower()
        
        # Add context based on keywords
        for category, keywords in self.categories.items():
            for keyword in keywords:
                if keyword.lower() in enhanced_text:
                    enhanced_text += f" {keyword}"
        
        return enhanced_text
    
    def classify_content(self, text: str, confidence_threshold: float = 0.3) -> Tuple[str, float]:
        """
        Classify content using zero-shot classification
        
        Args:
            text: Input text to classify
            confidence_threshold: Minimum confidence score
            
        Returns:
            Tuple of (category, confidence_score)
        """
        if not self.classifier:
            logger.warning("Classifier not loaded, using fallback classification")
            return self._fallback_classify(text)
        
        try:
            # Prepare text and labels
            enhanced_text = self._enhance_text_with_keywords(text)
            candidate_labels = self._prepare_candidate_labels()
            
            # Perform classification
            result = self.classifier(enhanced_text, candidate_labels)
            
            best_label = result['labels'][0]
            best_score = result['scores'][0]
            
            logger.info(f"Classification result: {best_label} (confidence: {best_score:.3f})")
            
            # Return result if confidence is above threshold
            if best_score >= confidence_threshold:
                return best_label, best_score
            else:
                logger.warning(f"Low confidence ({best_score:.3f}), using fallback")
                return self._fallback_classify(text)
                
        except Exception as e:
            logger.error(f"Error during classification: {e}")
            return self._fallback_classify(text)
    
    def _fallback_classify(self, text: str) -> Tuple[str, float]:
        """
        Fallback classification using keyword matching
        """
        text_lower = text.lower()
        
        # Keyword-based classification
        for category, keywords in self.categories.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    return category, 0.8  # High confidence for keyword match
        
        # Default category
        return "📄 НОВОЕ ИССЛЕДОВАНИЕ", 0.5
    
    def classify_batch(self, texts: List[str]) -> List[Tuple[str, float]]:
        """
        Classify multiple texts at once
        
        Args:
            texts: List of texts to classify
            
        Returns:
            List of (category, confidence) tuples
        """
        results = []
        for text in texts:
            result = self.classify_content(text)
            results.append(result)
        
        return results
    
    def get_categories_info(self) -> Dict[str, List[str]]:
        """Get information about available categories"""
        return self.categories.copy() 