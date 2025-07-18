"""
News Article Summarizer Module
Uses Transformers library for text summarization
"""

import logging
from typing import Optional
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import torch

logger = logging.getLogger(__name__)

class NewsSummarizer:
    def __init__(self, model_name: str = "facebook/bart-large-cnn"):
        """
        Initialize the summarizer with a pre-trained model
        
        Args:
            model_name: Hugging Face model name for summarization
        """
        self.model_name = model_name
        self.summarizer = None
        self.tokenizer = None
        self.max_input_length = 1024  # BART max input length
        self.max_summary_length = 500  # Max summary length
        self.min_summary_length = 100  # Min summary length
        
    def _load_model(self):
        """Load the summarization model"""
        if self.summarizer is None:
            try:
                logger.info(f"Loading summarization model: {self.model_name}")
                
                # Use GPU if available
                device = 0 if torch.cuda.is_available() else -1
                
                self.summarizer = pipeline(
                    "summarization",
                    model=self.model_name,
                    device=device,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
                )
                
                # Load tokenizer for text length checking
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                
                logger.info("Summarization model loaded successfully")
                
            except Exception as e:
                logger.error(f"Failed to load summarization model: {e}")
                raise
    
    def _prepare_text(self, text: str) -> str:
        """
        Prepare text for summarization by cleaning and truncating
        
        Args:
            text: Raw article text
            
        Returns:
            Cleaned and truncated text
        """
        # Clean the text
        text = text.strip()
        text = ' '.join(text.split())  # Normalize whitespace
        
        # Truncate if too long
        if self.tokenizer:
            tokens = self.tokenizer.encode(text, truncation=True, max_length=self.max_input_length)
            text = self.tokenizer.decode(tokens, skip_special_tokens=True)
        
        return text
    
    def _format_summary(self, summary: str) -> str:
        """
        Format summary into 3 paragraphs
        
        Args:
            summary: Raw summary text
            
        Returns:
            Formatted summary with paragraphs
        """
        # Split summary into sentences
        sentences = [s.strip() for s in summary.split('.') if s.strip()]
        
        if len(sentences) <= 3:
            # If 3 or fewer sentences, each gets its own paragraph
            return '\n\n'.join(sentences) + '.'
        
        # Distribute sentences across 3 paragraphs
        sentences_per_paragraph = len(sentences) // 3
        remainder = len(sentences) % 3
        
        paragraphs = []
        start = 0
        
        for i in range(3):
            # Add extra sentence to first paragraphs if there's remainder
            end = start + sentences_per_paragraph + (1 if i < remainder else 0)
            paragraph_sentences = sentences[start:end]
            
            if paragraph_sentences:
                paragraphs.append('. '.join(paragraph_sentences) + '.')
            
            start = end
        
        return '\n\n'.join(paragraphs)
    
    def summarize_article(self, title: str, content: str) -> str:
        """
        Summarize a news article to 3 paragraphs
        
        Args:
            title: Article title
            content: Article content
            
        Returns:
            Summarized article text (3 paragraphs)
        """
        try:
            # Load model if not already loaded
            self._load_model()
            
            # Combine title and content
            full_text = f"{title}. {content}"
            
            # Prepare text for summarization
            prepared_text = self._prepare_text(full_text)
            
            # Check if text is too short to summarize
            if len(prepared_text.split()) < 50:
                logger.warning("Text too short for summarization, returning original")
                return content[:500] + "..." if len(content) > 500 else content
            
            # Generate summary
            logger.info("Generating summary...")
            summary_result = self.summarizer(
                prepared_text,
                max_length=self.max_summary_length,
                min_length=self.min_summary_length,
                do_sample=False,
                num_beams=4
            )
            
            # Extract summary text
            summary = summary_result[0]['summary_text']
            
            # Format into 3 paragraphs
            formatted_summary = self._format_summary(summary)
            
            logger.info(f"Summary generated successfully ({len(formatted_summary)} characters)")
            return formatted_summary
            
        except Exception as e:
            logger.error(f"Error during summarization: {e}")
            # Fallback: return truncated original content
            return content[:500] + "..." if len(content) > 500 else content
    
    def should_summarize(self, source: str) -> bool:
        """
        Check if content from this source should be summarized
        
        Args:
            source: Source name/key
            
        Returns:
            True if should summarize, False otherwise
        """
        # Don't summarize X/Twitter content
        excluded_sources = ['twitter', 'x', 'tweet']
        
        return not any(excluded in source.lower() for excluded in excluded_sources) 