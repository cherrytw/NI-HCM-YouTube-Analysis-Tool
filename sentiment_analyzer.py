# sentiment_analyzer.py
from transformers import pipeline
import torch
from translator import TranslationService
from datasets import Dataset

import warnings
from transformers import logging

# Filter specific warning types
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', message='You seem to be using the pipelines sequentially on GPU.*')
logging.set_verbosity_error()

class SentimentAnalyzer:
    def __init__(self):
        self.device = 0 if torch.cuda.is_available() else -1
        self.classifier = pipeline(
            "zero-shot-classification",
            model="MoritzLaurer/deberta-v3-large-zeroshot-v2.0",
            device=self.device,
        )

    def get_sentiment_emoji(self, sentiment):
        sentiment_emojis = {
            "positive": "😊",
            "neutral": "😐",
            "negative": "😟",
            "enthusiastic": "🤩",
            "critical": "🤨",
        }
        return sentiment_emojis.get(sentiment, "❓")

    def get_topic_emoji(self, topic):
        topic_emojis = {
            "question": "❓",
            "opinion": "💭",
            "fact": "📚",
            "complaint": "😤",
            "praise": "👏",
            "suggestion": "💡",
        }
        return topic_emojis.get(topic, "📝")

    def get_relevance_emoji(self, score):
        if score >= 0.9:
            return "🎯"
        elif score >= 0.5:
            return "🔄"
        else:
            return "❌"

    def run_classification(self, texts, candidate_labels, hypothesis_template):
        """Run classification using dataset for better GPU utilization"""
        # Create dataset
        dataset = Dataset.from_dict({"text": texts})
        
        # Run classification
        results = []
        for output in self.classifier(
            dataset["text"],
            candidate_labels=candidate_labels,
            hypothesis_template=hypothesis_template,
            batch_size=8  # Adjust based on your GPU memory
        ):
            results.append(output)
            
        return results[0]  # Since we're only processing one text at a time

    def analyze_comment(self, text, context, is_reply=False):
        """Analyze comment with context-aware relevance"""
        try:
            # Translate comment to English if needed
            translated_text, original_lang = TranslationService.translate_to_english(
                text
            )

            # Run sentiment analysis
            sentiment_result = self.run_classification(
                [translated_text],
                candidate_labels=[
                    "positive",
                    "neutral",
                    "negative",
                    "enthusiastic",
                    "critical",
                ],
                hypothesis_template="This comment is {}"
            )

            # Run topic classification
            topic_result = self.run_classification(
                [translated_text],
                candidate_labels=[
                    "question",
                    "opinion",
                    "fact",
                    "complaint",
                    "praise",
                    "suggestion",
                ],
                hypothesis_template="This comment is a {}."
            )

            # Run relevance analysis
            relevance_template = (
                "This reply is {} to: " + context if is_reply else "This comment is {} to: " + context
            )
            relevance_result = self.run_classification(
                [translated_text],
                candidate_labels=["related", "unrelated"],
                hypothesis_template=relevance_template
            )

            # Calculate relevance score
            relevance_score = (
                round(relevance_result["scores"][0], 3)
                if relevance_result["labels"][0] == "related"
                else round(1 - relevance_result["scores"][0], 3)
            )

            return {
                "original_lang": original_lang,
                "translated_text": translated_text if original_lang != "en" else None,
                "sentiment": sentiment_result["labels"][0],
                "sentiment_score": round(sentiment_result["scores"][0], 3),
                "sentiment_emoji": self.get_sentiment_emoji(
                    sentiment_result["labels"][0]
                ),
                "topic": topic_result["labels"][0],
                "topic_score": round(topic_result["scores"][0], 3),
                "topic_emoji": self.get_topic_emoji(topic_result["labels"][0]),
                "relevance_score": relevance_score,
                "relevance_emoji": self.get_relevance_emoji(relevance_score),
            }

        except Exception as e:
            print(f"Analysis error: {str(e)}")
            return None