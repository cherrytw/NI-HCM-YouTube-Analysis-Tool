# analyzer.py
import requests
from utils import Utils
from config import Config
from youtube_service import YouTubeService
from sentiment_analyzer import SentimentAnalyzer
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from rich.text import Text
from rich import box
from rich.style import Style
from colors import COLORS
from rich.live import Live
import warnings

class YouTubeAnalyzer:
    def __init__(self):
        self.youtube_service = YouTubeService(Config.YOUTUBE_API_KEY)
        self.sentiment_analyzer = SentimentAnalyzer()
        self.console = Console()
        self.whole_input_for_analysis = None
    def create_comment_panel(
        self, author, text, analysis, is_reply=False, parent_author=None
    ):
        """Create comment panel"""
        header = Text()
        header.append(author, style=f"bold {COLORS['name']}")
        header.append(f" • 👍 {analysis.get('likes', 0)}", style=COLORS["text"])

        content = Text()
        content.append(f"\n{text}\n", style=COLORS["text"])

        # Only show translation if:
        # 1. Translation exists
        # 2. Original language is not English
        # 3. Translation is actually different from original text
        if (analysis.get("translated_text") and 
            analysis.get("original_lang") != "en" and 
            analysis.get("translated_text").lower().strip() != text.lower().strip()):
            content.append(
                f"\n🌐 English: {analysis['translated_text']}\n", style=COLORS["text"]
            )

        content.append("\n✨ Analysis:\n", style=f"bold {COLORS['name']}")
        
        content.append(
            f"• Sentiment: {analysis['sentiment_emoji']} {analysis['sentiment']} ({analysis['sentiment_score']:.2f})\n",
            style=COLORS["text"],
        )
        content.append(
            f"• Topic: {analysis['topic_emoji']} {analysis['topic']} ({analysis['topic_score']:.2f})\n",
            style=COLORS["text"],
        )

        if is_reply:
            content.append("• Relevance to ", style=COLORS["text"])
            content.append(f"@{parent_author}", style=f"bold {COLORS['name']}")
            content.append(f"'s comment: {analysis['relevance_emoji']} ({analysis['relevance_score']:.2f})",
                style=COLORS["text"],
            )
        else:
            content.append("• Relevance to ", style=COLORS["text"])
            content.append("video", style=f"bold {COLORS['title']}")
            content.append(f": {analysis['relevance_emoji']} ({analysis['relevance_score']:.2f})",
                style=COLORS["text"],
            )

        return Panel(
            Text.assemble(header, content),
            box=box.ROUNDED,
            border_style=Style(color=COLORS["border"]),
            title=self.format_panel_title("💬 " + ("Reply" if is_reply else "Comment")),
            title_align="left",
            style=f"on {COLORS['background']}",
        )

    def print_comments(self, comments, full_analysis_tuple):
        """Print comments and summary"""
        full_analysis, _ = full_analysis_tuple

        # Initialize enhanced summary statistics
        summary = {
            'total_comments': 0,
            'total_replies': 0,
            'likes': {
                'total': 0,
                'max': 0,
                'avg': 0
            },
            'sentiments': {
                'positive': {'count': 0, 'likes': 0},
                'neutral': {'count': 0, 'likes': 0},
                'negative': {'count': 0, 'likes': 0},
                'enthusiastic': {'count': 0, 'likes': 0},
                'critical': {'count': 0, 'likes': 0}
            },
            'topics': {
                'question': {'count': 0, 'relevance_avg': 0.0},
                'opinion': {'count': 0, 'relevance_avg': 0.0},
                'fact': {'count': 0, 'relevance_avg': 0.0},
                'complaint': {'count': 0, 'relevance_avg': 0.0},
                'praise': {'count': 0, 'relevance_avg': 0.0},
                'suggestion': {'count': 0, 'relevance_avg': 0.0}
            },
            'relevance': {
                'high': {'count': 0, 'likes': 0},
                'medium': {'count': 0, 'likes': 0},
                'low': {'count': 0, 'likes': 0},
                'total_score': 0.0
            },
            'engagement': {
                'most_liked': None,
                'most_relevant': None,
                'most_discussed': None  # For comments with most replies
            },
            'potential_issues': [],
            'thread_depth': {'max': 0, 'avg': 0},
            'time_analysis': {
                'response_patterns': {},  # If timestamps available
                'peak_activity': None
            }
        }

        main_tree = Tree(
            Text("Comment Analysis", style=COLORS["title"]), guide_style=COLORS["text"]
        )

        # Process comments and build tree
        self._process_comments_tree(comments, main_tree, full_analysis, summary)

        # Calculate averages and finalize statistics
        self._finalize_summary_stats(summary)

        # Print the comment tree
        self.console.print(main_tree)
        
        # Print enhanced summary
        self._print_enhanced_summary(summary)

    def _process_comments_tree(self, comments, tree, context, summary, depth=1, parent=None):
        """Recursively process comments and update summary"""
        for comment in comments:
            if not parent:  # Main comment
                summary['total_comments'] += 1
                analysis = self.sentiment_analyzer.analyze_comment(
                    comment["text"], context, is_reply=False
                )
            else:  # Reply
                summary['total_replies'] += 1
                analysis = self.sentiment_analyzer.analyze_comment(
                    comment["text"], parent["text"], is_reply=True
                )
            
            analysis["likes"] = comment.get("likes", 0)
            
            # Update summary statistics
            self._update_enhanced_stats(summary, analysis, comment, depth, parent)
            
            # Create comment panel
            panel = self.create_comment_panel(
                comment["author"],
                comment["text"],
                analysis,
                is_reply=bool(parent),
                parent_author=parent["author"] if parent else None
            )
            
            # Add to tree
            branch = tree.add(panel)
            
            # Process replies recursively
            if comment.get("replies"):
                self._process_comments_tree(
                    comment["replies"],
                    branch,
                    context,
                    summary,
                    depth + 1,
                    comment
                )

    def _update_enhanced_stats(self, summary, analysis, comment, depth, parent):
        """Update enhanced summary statistics"""
        likes = comment.get('likes', 0)
        
        # Update likes statistics
        summary['likes']['total'] += likes
        summary['likes']['max'] = max(summary['likes']['max'], likes)
        
        # Update sentiment statistics
        if analysis['sentiment'] in summary['sentiments']:
            summary['sentiments'][analysis['sentiment']]['count'] += 1
            summary['sentiments'][analysis['sentiment']]['likes'] += likes
        
        # Update topic statistics
        if analysis['topic'] in summary['topics']:
            topic_stats = summary['topics'][analysis['topic']]
            topic_stats['count'] += 1
            topic_stats['relevance_avg'] = (
                (topic_stats['relevance_avg'] * (topic_stats['count'] - 1) + 
                analysis['relevance_score']) / topic_stats['count']
            )
        
        # Update relevance statistics
        relevance_score = analysis['relevance_score']
        summary['relevance']['total_score'] += relevance_score
        if relevance_score >= 0.9:
            summary['relevance']['high']['count'] += 1
            summary['relevance']['high']['likes'] += likes
        elif relevance_score >= 0.5:
            summary['relevance']['medium']['count'] += 1
            summary['relevance']['medium']['likes'] += likes
        else:
            summary['relevance']['low']['count'] += 1
            summary['relevance']['low']['likes'] += likes
        
        # Update engagement tracking
        if likes > 0 and (not summary['engagement']['most_liked'] or 
                         likes > summary['engagement']['most_liked']['likes']):
            summary['engagement']['most_liked'] = {
                'text': comment['text'][:100] + '...' if len(comment['text']) > 100 else comment['text'],
                'likes': likes,
                'sentiment': analysis['sentiment'],
                'author': comment.get('author', 'Unknown')
            }
            
        if relevance_score > 0 and (not summary['engagement']['most_relevant'] or 
                                  relevance_score > summary['engagement']['most_relevant']['score']):
            summary['engagement']['most_relevant'] = {
                'text': comment['text'][:100] + '...' if len(comment['text']) > 100 else comment['text'],
                'score': relevance_score,
                'sentiment': analysis['sentiment'],
                'author': comment.get('author', 'Unknown')
            }
        
        # Track thread depth
        summary['thread_depth']['max'] = max(summary['thread_depth']['max'], depth)
        
        # Track potential issues
        if analysis['sentiment'] == 'negative' and analysis['relevance_score'] < 0.5:
            summary['potential_issues'].append({
                'text': comment['text'][:100] + '...' if len(comment['text']) > 100 else comment['text'],
                'author': comment.get('author', 'Unknown'),
                'relevance_score': analysis['relevance_score'],
                'likes': likes
            })

    def _finalize_summary_stats(self, summary):
        """Calculate final averages and statistics"""
        total_items = summary['total_comments'] + summary['total_replies']
        if total_items > 0:
            summary['likes']['avg'] = round(summary['likes']['total'] / total_items, 1)
            summary['thread_depth']['avg'] = round(
                summary['thread_depth']['max'] / summary['total_comments'], 1
            )

    def _print_enhanced_summary(self, summary):
        """Print enhanced comment analysis summary"""
        total_items = summary['total_comments'] + summary['total_replies']
        
        content = Text()
        #content.append(f"\n📊 ENHANCED COMMENT ANALYSIS\n", style=f"bold {COLORS['title']}")
        
        # Volume and Engagement
        content.append("\n💬 Interaction Statistics:\n", style=f"bold {COLORS['name']}")
        content.append(f"• Comments: {summary['total_comments']}\n", style=COLORS['text'])
        content.append(f"• Replies: {summary['total_replies']}\n", style=COLORS['text'])
        content.append(f"• Average Thread Depth: {summary['thread_depth']['avg']}\n", style=COLORS['text'])
        content.append(f"• Total Likes: {summary['likes']['total']}\n", style=COLORS['text'])
        content.append(f"• Average Likes per Comment: {summary['likes']['avg']}\n", style=COLORS['text'])
        
        # Sentiment Analysis
        content.append("\n😊 Sentiment Analysis:\n", style=f"bold {COLORS['name']}")
        for sentiment, stats in summary['sentiments'].items():
            if stats['count'] > 0:
                percentage = round((stats['count'] / total_items) * 100, 1)
                avg_likes = round(stats['likes'] / stats['count'], 1) if stats['count'] > 0 else 0
                content.append(
                    f"• {sentiment.title()}: {stats['count']} ({percentage}%) - Avg Likes: {avg_likes}\n",
                    style=COLORS['text']
                )
        
        # Topic Analysis
        content.append("\n💭 Topic Analysis:\n", style=f"bold {COLORS['name']}")
        for topic, stats in summary['topics'].items():
            if stats['count'] > 0:
                percentage = round((stats['count'] / total_items) * 100, 1)
                content.append(
                    f"• {topic.title()}: {stats['count']} ({percentage}%) - Avg Relevance: {stats['relevance_avg']:.3f}\n",
                    style=COLORS['text']
                )
        
        # Relevance Distribution
        content.append("\n🎯 Relevance Distribution:\n", style=f"bold {COLORS['name']}")
        for level, stats in summary['relevance'].items():
            if isinstance(stats, dict) and stats['count'] > 0:
                percentage = round((stats['count'] / total_items) * 100, 1)
                avg_likes = round(stats['likes'] / stats['count'], 1) if stats['count'] > 0 else 0
                content.append(
                    f"• {level.title()}: {stats['count']} ({percentage}%) - Avg Likes: {avg_likes}\n",
                    style=COLORS['text']
                )
        
        # Top Engagement
        content.append("\n🔥 Most Engaged Content:\n", style=f"bold {COLORS['name']}")
        if summary['engagement']['most_liked']:
            content.append("Most Liked Comment:\n", style=COLORS['text'])
            content.append(f"• Author: {summary['engagement']['most_liked']['author']}\n", style=COLORS['text'])
            content.append(f"• Text: {summary['engagement']['most_liked']['text']}\n", style=COLORS['text'])
            content.append(f"• Likes: {summary['engagement']['most_liked']['likes']}\n", style=COLORS['text'])
        
        if summary['engagement']['most_relevant']:
            content.append("\nMost Relevant Comment:\n", style=COLORS['text'])
            content.append(f"• Author: {summary['engagement']['most_relevant']['author']}\n", style=COLORS['text'])
            content.append(f"• Text: {summary['engagement']['most_relevant']['text']}\n", style=COLORS['text'])
            content.append(f"• Relevance Score: {summary['engagement']['most_relevant']['score']:.3f}\n", style=COLORS['text'])
        
        # Potential Issues
        if summary['potential_issues']:
            content.append("\n⚠️ Potential Issues:\n", style=f"bold {COLORS['name']}")
            content.append(f"• Total flagged comments: {len(summary['potential_issues'])}\n", style=COLORS['text'])
            top_issues = sorted(summary['potential_issues'], key=lambda x: x['likes'], reverse=True)[:3]
            for issue in top_issues:
                content.append(f"• [{issue['likes']} likes] {issue['author']}: {issue['text']}\n", style=COLORS['text'])

        self.console.print(Panel(
            content,
            box=box.ROUNDED,
            border_style=Style(color=COLORS["border"]),
            title=self.format_panel_title("📊 ENHANCED COMMENT ANALYSIS"),
            title_align="left",
            style=f"on {COLORS['background']}"
        ))

    def add_replies_to_tree(
        self, replies, parent_branch, full_analysis, parent_comment
    ):
        """Add replies to tree"""
        for reply in replies:
            analysis = self.sentiment_analyzer.analyze_comment(
                reply["text"], parent_comment["text"], is_reply=True
            )
            # Add likes count to analysis dictionary
            analysis['likes'] = reply.get('likes', 0)

            reply_panel = self.create_comment_panel(
                reply["author"],
                reply["text"],
                analysis,
                is_reply=True,
                parent_author=parent_comment["author"],
            )

            reply_branch = parent_branch.add(reply_panel)

            if reply["replies"]:
                self.add_replies_to_tree(
                    reply["replies"], reply_branch, full_analysis, reply
                )   
    def get_word_count(self, text):
        """Count words in text"""
        return len(text.split())

    def format_panel_title(self, title_text):
        """Consistent panel title formatting"""
        return f"[bold {COLORS['title']}]{title_text}[/]"

    def chunk_transcript(self, transcript, chunk_size=2000):  # chunk_size is number of words
        """Split transcript into chunks of specified number of words"""
        words = transcript.split()
        chunks = []

        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i : i + chunk_size])
            chunks.append(chunk)

        return chunks
    def format_video_content(self, video_info):
        """Format video details content"""
        content = Text()
        content.append(video_info["Title"], style=COLORS["name"])
        content.append("\n\n")
        content.append(f"📺 Channel: {video_info['Channel']}\n", style=COLORS["text"])
        content.append(f"👀 Views: {video_info['View Count']}\n", style=COLORS["text"])
        content.append(f"👍 Likes: {video_info['Like Count']}\n", style=COLORS["text"])
        content.append(
            f"💬 Comments: {video_info['Comment Count']}\n", style=COLORS["text"]
        )
        content.append(f"⏱️ Duration: {video_info['Duration']}\n", style=COLORS["text"])
        content.append(
            f"📅 Published: {video_info['Published At']}\n", style=COLORS["text"]
        )

        if video_info.get("Description"):
            content.append(f"\n📝 {video_info['Description']}", style=COLORS["text"])
        return content

    def format_language_content(self, transcript_language, detected_language):
        """Format language information content"""
        content = Text()
        content.append(
            f"🔤 Transcript Language: {transcript_language}\n", style=COLORS["text"]
        )
        content.append(
            f"🌐 Detected Language: {detected_language}", style=COLORS["text"]
        )
        return content

    def get_formatted_video_info(self, video_info, transcript_language, detected_language):
        """Get formatted video info without transcript preview"""
        content = Text()

        # Video title at the top
        content.append("Title: ", style=f"bold {COLORS['label']}")
        content.append(f"{video_info['Title']}\n", style=f"bold {COLORS['name']}")
        content.append("─" * 50 + "\n", style=COLORS['text'])

        # Video Details Section
        content.append("\n📋 VIDEO DETAILS\n", style=f"bold {COLORS['title']}")
        
        # Add URL line after title
        content.append("🔗 ", style=COLORS['text'])
        content.append("URL: ", style=f"bold {COLORS['label']}")
        content.append(f"https://www.youtube.com/watch?v={video_info['video_id']}\n", style=COLORS['text'])
        
        content.append("📺 ", style=COLORS['text'])
        content.append("Channel: ", style=f"bold {COLORS['label']}")
        content.append(f"{video_info['Channel']}\n", style=COLORS['text'])
        content.append("👀 ", style=COLORS['text'])
        content.append("Views: ", style=f"bold {COLORS['label']}")
        content.append(f"{video_info['View Count']}\n", style=COLORS['text'])
        content.append("👍 ", style=COLORS['text'])
        content.append("Likes: ", style=f"bold {COLORS['label']}")
        content.append(f"{video_info['Like Count']}\n", style=COLORS['text'])
        content.append("💬 ", style=COLORS['text'])
        content.append("Comments: ", style=f"bold {COLORS['label']}")
        content.append(f"{video_info['Comment Count']}\n", style=COLORS['text'])
        content.append("⏱️ ", style=COLORS['text'])
        content.append("Duration: ", style=f"bold {COLORS['label']}")
        content.append(f"{video_info['Duration']}\n", style=COLORS['text'])
        content.append("📅 ", style=COLORS['text'])
        content.append("Published: ", style=f"bold {COLORS['label']}")
        content.append(f"{video_info['Published At']}\n", style=COLORS['text'])

        # Language Information Section
        content.append("\n" + "─" * 50 + "\n", style=COLORS["text"])
        content.append("\n🌍 LANGUAGE INFORMATION\n", style=f"bold {COLORS['title']}")
        content.append("🔤 ", style=COLORS["text"])
        content.append("Transcript Language: ", style=f"bold {COLORS['label']}")
        content.append(f"{transcript_language}\n", style=COLORS["text"])
        content.append("🌐 ", style=COLORS["text"])
        content.append("Detected Language: ", style=f"bold {COLORS['label']}")
        content.append(f"{detected_language}\n", style=COLORS["text"])

        return content
    def format_combined_info(self, video_info, transcript_language, detected_language, transcript_preview, transcript):
        """Create a single unified panel for all video information"""
        # Get formatted video info
        content = self.get_formatted_video_info(
            video_info, transcript_language, detected_language
        )
        video_info_text = content.plain
        
        # Add transcript preview section for display
        content.append("\n" + "─" * 50 + "\n", style=COLORS['text'])
        content.append("\n📝 TRANSCRIPT PREVIEW\n", style=f"bold {COLORS['title']}")
        content.append("📊 ", style=COLORS['text'])
        content.append("Word Count: ", style=f"bold {COLORS['label']}")
        content.append(f"{self.get_word_count(transcript):,} words\n\n", style=COLORS['text'])
        content.append(transcript_preview, style=COLORS['text'])
        
        # Combine video info with full transcript for chunking
        self.whole_input_for_analysis = f"{video_info_text}\n\nFULL TRANSCRIPT:\n\n{transcript}"
        
        return Panel(
            content,
            box=box.ROUNDED,
            border_style=Style(color=COLORS['border']),
            title=self.format_panel_title("📊 VIDEO INFORMATION"),
            title_align="left",
            style=f"on {COLORS['background']}"
        )
    
    def format_analysis_content(self, analysis_text):
        """Format analysis content"""
        content = Text()
        sections = analysis_text.split("\n\n")

        for section in sections:
            if section.strip():
                if any(
                    emoji in section[:2]
                    for emoji in ["📌", "🎯", "🔑", "💭", "📊", "🎭", "🗣️", "🏷️"]
                ):
                    header, *rest = section.split("\n", 1)
                    content.append(f"\n{header}\n", style=COLORS["label"])
                    if rest:
                        content.append(f"{rest[0]}\n", style=COLORS["text"])
                else:
                    content.append(f"{section}\n", style=COLORS["text"])

        return content

    def format_analysis_output(self, analysis_text):
        """Format analysis results panel"""
        return Panel(
            self.format_analysis_content(analysis_text),
            box=box.ROUNDED,
            border_style=Style(color=COLORS["border"]),
            title=self.format_panel_title("📊 ANALYSIS RESULTS"),
            title_align="left",
            style=f"on {COLORS['background']}",
        )
        
    def analyze_transcript_with_ollama(self, detected_language, video_title):
        """Analyze transcript sequentially, building upon previous chunks"""
        chunks = self.chunk_transcript(self.whole_input_for_analysis)
        total_chunks = len(chunks)
        
        progress_content = Text()
        progress_content.append(
            f"\n📊 Analyzing transcript in {total_chunks} parts sequentially...\n",
            style=f"bold {COLORS['title']}",
        )

        # Initialize cumulative analysis
        cumulative_analysis = None

        # Create panel that will be updated
        progress_panel = Panel(
            progress_content,
            box=box.ROUNDED,
            border_style=Style(color=COLORS["border"]),
            style=f"on {COLORS['background']}",
        )

        # Use Live display context manager
        with Live(progress_panel, refresh_per_second=10) as live:
            for i, chunk in enumerate(chunks, 1):
                # Get word count for current chunk
                word_count = len(chunk.split())
                progress_content.append(
                    f"✓ Processing Part {i}/{total_chunks} ({word_count:,} words)\n", 
                    style=COLORS["text"]
                )
                live.update(
                    Panel(
                        progress_content,
                        box=box.ROUNDED,
                        border_style=Style(color=COLORS["border"]),
                        style=f"on {COLORS['background']}",
                    )
                )

                # Generate prompt based on whether we have previous analysis
                if cumulative_analysis is None:
                    # First chunk - initial analysis
                    prompt = self._create_initial_analysis_prompt(chunk, i, total_chunks, detected_language, video_title)
                else:
                    # Subsequent chunks - update existing analysis
                    prompt = self._create_update_analysis_prompt(chunk, cumulative_analysis, i, total_chunks, detected_language, video_title)

                try:
                    response = requests.post(
                        Config.OLLAMA_API_URL,
                        json={"model": "llama3", "prompt": prompt, "stream": False}
                    )
                    response.raise_for_status()
                    cumulative_analysis = response.json()["response"]
                except requests.RequestException as e:
                    self.console.print(Text(f"Error analyzing chunk: {str(e)}", style=COLORS['name']))
                    return f"Analysis error in part {i}"

            progress_content.append(
                "\n✨ Analysis complete!\n", style=f"bold {COLORS['title']}"
            )
            live.update(
                Panel(
                    progress_content,
                    box=box.ROUNDED,
                    border_style=Style(color=COLORS["border"]),
                    style=f"on {COLORS['background']}",
                )
            )

        return cumulative_analysis, None  # Return None for comment_context since we're not using it
    def _create_initial_analysis_prompt(self, chunk, chunk_num, total_chunks, detected_language, video_title):
        """Create prompt for the first chunk analysis"""
        return f"""Please analyze this first part ({chunk_num}/{total_chunks}) of the video transcript. Create an initial analysis in this format:

📌 SUMMARY
Write 10 sentences capturing the main content so far.

🎯 MAIN TOPIC & CONTEXT
• Primary subject matter identified so far
• Context and background
• Target audience
• Purpose of the video (based on current understanding)

🔑 KEY POINTS & ARGUMENTS
• List main points identified so far
• Include supporting evidence where available

💭 TONE & PRESENTATION
• Overall tone observed
• Speaker's attitude
• Communication style
• Use of emotional appeals or logical arguments

📊 FACTUAL CONTENT
• Statistics or data presented
• Technical information
• Expert opinions or citations

🗣️ NOTABLE QUOTES
• Significant quotes from this section
• Context for each quote

🏷️ KEYWORDS & THEMES
List of 10 important keywords or themes identified so far.

Video Title: {video_title}
Current Section: Part {chunk_num} of {total_chunks}

Important: Provide in {detected_language} language.

Transcript chunk: {chunk}"""

    def _create_update_analysis_prompt(self, chunk, previous_analysis, chunk_num, total_chunks, detected_language, video_title):
        """Create prompt for updating existing analysis with new chunk"""
        return f"""Based on the previous analysis and this new section ({chunk_num}/{total_chunks}), update the analysis. Consider how this new information changes or reinforces previous understanding.

Previous Analysis:
{previous_analysis}

New Transcript Chunk:
{chunk}

Update the analysis in the same format:

📌 SUMMARY
Update the summary incorporating new information.

🎯 MAIN TOPIC & CONTEXT
• Refine or expand primary subject matter
• Add new context or background
• Update target audience understanding
• Clarify or modify purpose

🔑 KEY POINTS & ARGUMENTS
• Update existing points with new information
• Add new main points revealed
• Integrate new evidence or examples

💭 TONE & PRESENTATION
• Note any changes in tone
• Update speaker's attitude analysis
• Refine understanding of communication style
• Add new emotional/logical appeals

📊 FACTUAL CONTENT
• Add new statistics or data
• Integrate new technical information
• Add new expert opinions or citations

🗣️ NOTABLE QUOTES
• Add significant new quotes
• Provide context for new quotes
• Update significance of previous quotes if needed

🏷️ KEYWORDS & THEMES
Update keywords and themes based on new information.

Video Title: {video_title}
Current Section: Part {chunk_num} of {total_chunks}

Important: Maintain {detected_language} language and integrate new information smoothly with existing analysis."""
