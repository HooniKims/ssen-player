import unittest
from app.youtube_url import video_id
from app.media_tools import resource


class YouTubeTests(unittest.TestCase):
    def test_urls(self):
        for value in ('M7lc1UVf-VE','https://youtu.be/M7lc1UVf-VE?t=8',
                      'https://www.youtube.com/watch?v=M7lc1UVf-VE&list=x',
                      'https://youtube.com/shorts/M7lc1UVf-VE',
                      'https://www.youtube-nocookie.com/embed/M7lc1UVf-VE'):
            self.assertEqual(video_id(value),'M7lc1UVf-VE')
        for value in ('javascript:alert(1)','https://youtube.com.evil.test/watch?v=M7lc1UVf-VE',
                      'https://example.com/M7lc1UVf-VE','https://youtube.com/watch?v=<script>'):
            with self.assertRaises(ValueError): video_id(value)

    def test_brave_filter_engine(self):
        import adblock
        filters=adblock.FilterSet()
        filters.add_filters(resource('assets/web/adblock.txt').read_text('utf-8').splitlines())
        engine=adblock.Engine(filters)
        self.assertTrue(engine.check_network_urls('https://googleads.g.doubleclick.net/pagead/ad',
                         'https://www.youtube.com','script').matched)
        self.assertFalse(engine.check_network_urls('https://rr1.googlevideo.com/videoplayback',
                         'https://www.youtube.com','media').matched)


if __name__=='__main__': unittest.main()
