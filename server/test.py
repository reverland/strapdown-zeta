#!/usr/bin/env python2

import os
import sys
import unittest
import random
import string
import tempfile
import subprocess
import socket
import requests
import time
import shutil


def check_port(p):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    return sock.connect_ex(('127.0.0.1', p)) == 0


def random_name(length=10):
    return ''.join([random.choice(string.ascii_letters) for i in xrange(length)])

tmpfolders = []

class Test(unittest.TestCase):

    def writefile(self, fp, s):
        f = open(os.path.join(self.cwd, fp), 'w')
        f.write(s)
        f.close()

    def setUp(self):
        self.cwd = tempfile.mkdtemp()
        tmpfolders.append(self.cwd)
        self.title = ''.join([random.choice(string.printable[:62]) for x in range(20)])
        self.ports = [random.randint(60000, 65535) for x in range(4)]
        self.writefile(".md", "# Wiki Index Page\n\nStrapdown Rocks!\n\n")
        if not os.path.exists("./server"):
            print './server not found'
            sys.exit(10)

        args = ["./server", "-verbose", "-dir=" + self.cwd, "-toc=true", "-title=" + self.title, "-init", "-heading_number=i", "-addr=" + ','.join(map(lambda x: '127.0.0.1:%d' % x, self.ports))]
        print args
        self.proc = subprocess.Popen(args, stdout=subprocess.PIPE)

        while True:
            for i in self.ports:
                if check_port(i):
                    print("test port true")
                    break
            else:
                continue
            break
        # wait other ports avaliable
        time.sleep(0.5)
        self.ports = filter(check_port, self.ports)
        self.assertGreater(len(self.ports), 0)

    def test_index(self):
        text = u"This is a test"
        self.writefile(".md", text)
        r = requests.get("http://127.0.0.1:%d/" % self.ports[0])
        self.assertIn(self.title, r.text)
        self.assertIn(unicode(text), r.text)
        self.assertGreater(len(r.text), len(text))

    def test_raw_index(self):
        text = u"This is a test"
        self.writefile(".md", text)
        r = requests.get("http://127.0.0.1:%d/.md" % self.ports[0])
        self.assertEqual(text, r.text)

    def test_normal_post(self):
        text = u"This is a test"
        url = "http://127.0.0.1:%d/test" % self.ports[0]
        r = requests.get(url)
        self.assertIn("edit.min.js", r.text)

        self.writefile("test.md", text)
        r = requests.get(url)
        self.assertIn("strapdown.min.js", r.text)
        self.assertIn(text, r.text)

        r = requests.get(url + "?edit")
        self.assertIn(text, r.text)
        self.assertIn("edit.min.js", r.text)

        r = requests.get(url + "?history")
        self.assertEqual(u'No commit history found for test.md\n', r.text)

        r = requests.get(url + "?diff")
        self.assertEqual(u'Bad Parameter,please select TWO versions!\n', r.text)

        text = u"this is not a text"
        r = requests.post(url + "?edit", data={
            "body": text
        })
        self.assertIn(text, r.text)

    def test_dir_issue(self):
        folder1_name = random_name()
        folder1 = os.path.join(self.cwd, folder1_name)
        url = "http://127.0.0.1:%d/" % self.ports[0]

        r = requests.get(url+folder1_name+"/")
        self.assertIn("edit.min.js", r.text)

        os.makedirs(folder1)
        r = requests.get(url+folder1_name)
        self.assertIn('id="list"', r.text)

        text = 'This is some text'
        self.writefile(os.path.join(folder1, ".md"), text)
        r = requests.get(url+folder1_name)
        self.assertIn('strapdown.min.js', r.text)
        self.assertIn(text, r.text)

        folder2 = random_name() + ".md"
        os.makedirs(os.path.join(self.cwd, folder2))
        r = requests.get(url+folder2)
        self.assertIn('id="list"', r.text)
        r = requests.get(url+folder2[:-3])
        self.assertIn(url+folder2, r.url)
        self.assertIn('id="list"', r.text)

    def test_upload(self):
        randomFile = os.urandom(20)
        filename = random_name() + '.mp4'
        r = requests.post("http://127.0.0.1:%d/%s" % (self.ports[0], filename), files={
            "body": (filename, randomFile)
        })
        self.assertEqual(r.content, randomFile)
        self.assertEqual(open(os.path.join(self.cwd, filename), 'rb').read(), randomFile)
        self.assertEqual(r.headers['Content-Type'], "video/mp4")

    def test_upload_without_ext(self):
        randomFile = os.urandom(20)
        filename = random_name()
        r = requests.post("http://127.0.0.1:%d/%s" % (self.ports[0], filename), files={
            "body": (filename, randomFile)
        })
        self.assertEqual(r.content, randomFile)
        self.assertEqual(open(os.path.join(self.cwd, filename), 'rb').read(), randomFile)
        self.assertEqual(r.headers['Content-Type'], "application/octet-stream")

    def test_content_type_for_static(self):
        self.writefile("www.css", "xxx")
        r = requests.get("http://127.0.0.1:%d/www.css" % self.ports[0])
        self.assertEqual(r.headers['Content-Type'], "text/css; charset=utf-8")

    def test_upload_option_json(self):
        r = requests.post("http://127.0.0.1:%d/test.option.json" % self.ports[0], data={
            "body": "some words"
        }, allow_redirects=False)
        self.assertGreater(r.status_code, 300)
        self.assertLess(r.status_code, 400)

    def tearDown(self):
        self.proc.terminate()
        self.proc.wait()


if __name__ == '__main__':
    if os.path.dirname(sys.argv[0]):
        os.chdir(os.path.dirname(sys.argv[0]))
    suite = unittest.TestLoader().loadTestsFromTestCase(Test)
    rs = unittest.TextTestRunner(verbosity=2).run(suite)
    if len(rs.errors) > 0 or len(rs.failures) > 0:
        sys.exit(10)
    else:
        for i in tmpfolders:
            shutil.rmtree(i)
        sys.exit(0)
