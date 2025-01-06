import sys
from analyzer import YouTubeAnalyzer
from utils import Utils, OutputManager
from formatting import format_transcript_preview
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box
from colors import COLORS
import warnings


def main():
    console = Console()
    analyzer = YouTubeAnalyzer()

    try:
        # First get video URL
        video_url = console.input(
            Panel(
                f"[bold {COLORS['title']}]Enter YouTube URL:[/]",
                style=f"on {COLORS['background']}",
                border_style=COLORS["border"],
                box=box.ROUNDED,
            )
        )
        video_id = Utils.get_video_id(video_url)

        if not video_id:
            console.print(
                Panel(
                    f"[bold {COLORS['name']}]Invalid YouTube URL[/]",
                    style=f"on {COLORS['error_bg']}",
                    border_style=COLORS["name"],
                    box=box.ROUNDED,
                )
            )
            return

        # Get video info first
        video_info = analyzer.youtube_service.get_video_details(video_id)
        if not video_info:
            console.print(
                Panel(
                    f"[bold {COLORS['name']}]Could not retrieve video details[/]",
                    style=f"on {COLORS['error_bg']}",
                    border_style=COLORS["name"],
                    box=box.ROUNDED,
                )
            )
            return

        transcript_text, detected_language, transcript_language = (
            analyzer.youtube_service.get_transcript(video_id)
        )

        if isinstance(transcript_text, str) and not transcript_text.startswith(
            "An error occurred"
        ):
            # Display video information first
            console.print(
                analyzer.format_combined_info(
                    video_info,
                    transcript_language,
                    detected_language,
                    format_transcript_preview(transcript_text),
                    transcript_text,
                )
            )

            # Perform sequential analysis
            full_analysis, _ = analyzer.analyze_transcript_with_ollama(
                detected_language,
                video_info["Title"],
            )

            # Display analysis results
            console.print(analyzer.format_analysis_output(full_analysis))

            # Now ask for number of comments to analyze
            total_comments = int(video_info["Comment Count"])
            try:
                max_comments_prompt = f"Enter number of comments to analyze (1-{total_comments}, default=all [{total_comments} comments]):"
                max_comments_input = console.input(
                    Panel(
                        f"[bold {COLORS['title']}]{max_comments_prompt}[/]",
                        style=f"on {COLORS['background']}",
                        border_style=COLORS["border"],
                        box=box.ROUNDED,
                    )
                )
                max_comments = (
                    int(max_comments_input) if max_comments_input else total_comments
                )
                max_comments = min(
                    max_comments, total_comments
                )  # Ensure we don't exceed total
            except ValueError:
                console.print(
                    Panel(
                        f"[bold {COLORS['name']}]Using all {total_comments} comments[/]",
                        style=f"on {COLORS['error_bg']}",
                        border_style=COLORS["name"],
                        box=box.ROUNDED,
                    )
                )
                max_comments = total_comments

            # Fetch and print comments
            comments = analyzer.youtube_service.get_video_comments(
                video_id, max_comments=max_comments
            )
            if isinstance(comments, list):
                analyzer.print_comments(comments, (full_analysis, None))
            else:
                console.print(
                    Panel(
                        f"[bold {COLORS['name']}]Error: {comments}[/]",
                        style=f"on {COLORS['error_bg']}",
                        border_style=COLORS["name"],
                        box=box.ROUNDED,
                    )
                )

        else:
            console.print(
                Panel(
                    f"[bold {COLORS['name']}]Error: {transcript_text}[/]",
                    style=f"on {COLORS['error_bg']}",
                    border_style=COLORS["name"],
                    box=box.ROUNDED,
                )
            )

    except Exception as e:
        console.print(
            Panel(
                f"[bold {COLORS['name']}]An error occurred: {str(e)}[/]",
                style=f"on {COLORS['error_bg']}",
                border_style=COLORS["name"],
                box=box.ROUNDED,
            )
        )

if __name__ == "__main__":
    main() #www.youtube.com/watch?v=ag-KxYS8Vuw #https://www.youtube.com/watch?v=1ES9WSVFY0Q

