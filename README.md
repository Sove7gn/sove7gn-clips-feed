# sove7gn.clips feed

Queue + videos for the Instagram meme page @sove7gn.clips.
A Claude cloud routine posts the next reel 5x/day (9, 12, 3, 6, 9 IST) by running `post_next.py` in a Composio workbench.

- `queue.json` - reels waiting to be posted, in order (already-posted ones are skipped automatically by checking the page's captions)
- `posted.json` - record of what's already been posted
- `reels/` - the videos
