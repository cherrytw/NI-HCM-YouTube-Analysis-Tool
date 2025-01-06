# comment_analyzer.py
from thefuzz import fuzz
from utils import Utils

class CommentAnalyzer:
    @staticmethod
    def find_reply_target(
        reply_text, reply_author, all_authors, root_author, threshold=60
    ):
        text = "".join(c.lower() for c in reply_text if c.isalnum())
        best_match = None
        best_ratio = threshold

        for author in all_authors:
            if author != reply_author:
                clean_author = "".join(c.lower() for c in author if c.isalnum())
                if len(clean_author) >= 4:
                    ratio = fuzz.partial_ratio(clean_author, text)
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_match = author

        return best_match if best_match else root_author

    @staticmethod
    def extract_authors_and_replies(comments_data):
        comments_structure = []

        for comment_thread in comments_data:  # Removed the [:50] slice
            root_comment = comment_thread["snippet"]["topLevelComment"]["snippet"]
            root_author = root_comment["authorDisplayName"]
            authors = {root_author}

            comment_info = {
                "author": root_author,
                "text": root_comment["textDisplay"],
                "likes": root_comment["likeCount"],
                "published_at": root_comment["publishedAt"],
                "replies": [],
            }

            if "replies" in comment_thread:
                replies = comment_thread["replies"]["comments"]
                replies.sort(key=lambda x: x["snippet"]["publishedAt"])

                replies_by_author = {}
                conversation_chains = {}

                for reply in replies:
                    reply_author = reply["snippet"]["authorDisplayName"]
                    authors.add(reply_author)
                    reply_text = reply["snippet"]["textDisplay"]

                    target_author = CommentAnalyzer.find_reply_target(
                        reply_text, reply_author, authors, root_author
                    )

                    reply_info = {
                        "author": reply_author,
                        "text": reply_text,
                        "likes": reply["snippet"]["likeCount"],
                        "published_at": reply["snippet"]["publishedAt"],
                        "replying_to": target_author,
                        "replies": [],
                    }

                    if target_author in replies_by_author:
                        last_reply = replies_by_author[target_author]
                        last_reply["replies"].append(reply_info)
                        conversation_chains[reply_author] = target_author
                    else:
                        comment_info["replies"].append(reply_info)

                    replies_by_author[reply_author] = reply_info

            comments_structure.append(comment_info)

        return comments_structure
