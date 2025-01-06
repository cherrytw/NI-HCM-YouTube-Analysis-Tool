# youtube_service.py
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi
from translator import TranslationService
from comment_analyzer import CommentAnalyzer


class YouTubeService:
    def __init__(self, api_key):
        self.api_key = api_key
        self.youtube = build("youtube", "v3", developerKey=api_key)

    def get_video_details(self, video_id):
        try:
            video_response = (
                self.youtube.videos()
                .list(part="snippet,contentDetails,statistics", id=video_id)
                .execute()
            )

            if not video_response["items"]:
                return None

            video_data = video_response["items"][0]

            return {
                "video_id": video_id,
                "Title": video_data["snippet"]["title"],
                "Channel": video_data["snippet"]["channelTitle"],
                "Published At": video_data["snippet"]["publishedAt"],
                "View Count": video_data["statistics"]["viewCount"],
                "Like Count": video_data["statistics"].get("likeCount", "N/A"),
                "Comment Count": video_data["statistics"].get("commentCount", "N/A"),
                "Duration": video_data["contentDetails"]["duration"],
                "Description": video_data["snippet"]["description"][:200] + "...",
            }

        except HttpError as e:
            print(f"An HTTP error occurred: {e.resp.status} {e.content}")
            return None
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return None

    def get_video_comments(self, video_id, max_comments=100):
        """
        Fetch video comments with pagination support
        max_comments: maximum number of comments to fetch (default 100)
        """
        try:
            comments = []
            next_page_token = None

            while len(comments) < max_comments:
                request = (
                    self.youtube.commentThreads()
                    .list(
                        part="snippet,replies",
                        videoId=video_id,
                        maxResults=min(100, max_comments - len(comments)),
                        pageToken=next_page_token,
                    )
                    .execute()
                )

                comments.extend(request["items"])
                next_page_token = request.get("nextPageToken")
                if not next_page_token or len(comments) >= max_comments:
                    break

            return CommentAnalyzer.extract_authors_and_replies(comments)

        except HttpError as e:
            if e.resp.status == 403:
                return f"Comments are disabled for this video or API quota exceeded: {str(e)}"
            return f"An HTTP error occurred: {str(e)}"
        except Exception as e:
            return f"An error occurred while fetching comments: {str(e)}"

    def get_transcript(self, video_id):
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = next(iter(transcript_list))
            full_transcript = " ".join([entry["text"] for entry in transcript.fetch()])
            detected_lang = TranslationService.detect_language(full_transcript)
            return full_transcript, detected_lang, transcript.language_code
        except Exception as e:
            return f"An error occurred: {str(e)}", None, None
