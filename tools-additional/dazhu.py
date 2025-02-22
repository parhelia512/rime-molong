#!/usr/bin/env python3
import argparse
import opencc
import os
from collections import defaultdict
import re


class FakeOpenCC:
    def convert(text):
        return text


class Table:
    def __init__(self):
        self.w2c = defaultdict(list)
        self.c2w = defaultdict(list)

    def get_long_code(self, word):
        for code in self.w2c[word]:
            if len(code) >= 2:
                return code
        raise KeyError(f'{word} 無長碼, codes = {self.w2c[word]}')

    def has_quick_code(self, word, code):
        all_codes = self.w2c[word]
        for c in all_codes:
            if code.startswith(c) and len(c) < 4:
                return True
        return False

    def add(self, word, code, w=0):
        if not code:
            try:
                code = self.encode(word)
            except KeyError as e:
                print('# 無法編碼 %s : %s' % (word, str(e)))
                return
        if self.has_quick_code(word, code):
            # print('讓全', word, code)
            w = 0

        if code not in self.w2c[word]:
            self.w2c[word].append(code)
        if (word, w) not in self.c2w[code]:
            self.c2w[code].append((word, w))

        self.c2w[code].sort(key=lambda pair: pair[1], reverse=True)
        # if len(word)== 3:
        #     print('added %s %s' % (word, code))

    def encode(self, word):
        if len(word) == 1:
            raise KeyError('無碼單字: %s' % word)
        elif len(word) == 2:
            return self.get_long_code(word[0])[:2] + self.get_long_code(word[1])[:2]
        elif len(word) == 3:
            return self.get_long_code(word[0])[0] + self.get_long_code(word[1])[0] + self.get_long_code(word[2])[:2]
        else:
            return self.get_long_code(word[0])[0] + self.get_long_code(word[1])[0] + self.get_long_code(word[2])[0] + self.get_long_code(word[-1])[0]

    def print_c2w(self, file):
        for code, pairs in self.c2w.items():
            words = [pair[0] for pair in pairs]
            print(code + '\t' + '\t'.join(words), file=file)

    def print_w2c(self, file):
        for word, codes in self.w2c.items():
            for code in codes:
                print(f'{word}	{code}')


def make_opencc(config):
    if not config:
        return FakeOpenCC()
    cwd = os.getcwd()
    os.chdir('../rime-moran/opencc/')
    cc = opencc.OpenCC(config)
    os.chdir(cwd)
    return cc

table = Table()

def main(args):
    cc = make_opencc(args.opencc)
    folder = args.folder
    extended = args.extended
    output = args.output
    fulllist = args.fulllist
    global table

    # fixed table
    if fulllist:
        print("Generating fixed table")
        with open('../' + folder + '/moran_fixed_simp.dict.yaml', 'r') as f:
            deferred = []
            for l in f:
                matches = re.findall(r'^([^\t]+)\t([a-z;]+)\t?([a-z]+)?', l)
                if matches:
                    word, code, stem = matches[0]
                    if stem:
                        # stem should be added at the end of the list of codes of this char
                        deferred.append((word, stem))
                else:
                    matches = re.findall(r'^\w+$', l)
                    if not matches: continue
                    word = matches[0]
                    code = None
                word = cc.convert(word)
                table.add(word, code)
            for (word, stem) in deferred:
                table.add(word, stem)

    # chars
    print("Generating character table")
    with open('../' + folder + '/moran.chars.dict.yaml', 'r') as f:
        for l in f:
            matches = re.findall(r'(\w+)\t([a-zA-Z]+;[a-zA-Z]+)\t(\d+)', l)
            if not matches: continue
            char, code, w = matches[0]
            w = int(w)
            table.add(char, ''.join(code.split(';')) + '/', w)

    # base
    if fulllist:
        print("Generating base table")
        with open('../' + folder + '/moran.base.dict.yaml', 'r') as f:
            for l in f:
                matches = re.findall(r'[a-z]{2};[a-z]{2}', l)
                if not matches: continue
                parts = l.split('\t')
                word = parts[0]
                codes = parts[1]

                pairs = codes.split()
                parts_before_semicolon = [pair.split(';')[0] for pair in pairs]

                code = ''.join(parts_before_semicolon)
                table.add(word, code)

    # liangfen
    if fulllist:
        print("Generating liangfen table")
        with open('../' + folder + '/zrlf.dict.yaml', 'r') as f:
            for l in f:
                matches = re.findall(r'(\w+)\t([a-z]+)', l)
                if not matches: continue
                char, code = matches[0]
                table.add(char, 'olf' + code)

    # stroke
    if fulllist:
        print("Generating stroke table")
        with open('stroke.dict.yaml') as f:
            for l in f:
                matches = re.findall(r'(\w+)\t([a-z]+)', l)
                if not matches: continue
                char, code = matches[0]
                table.add(char, 'obh' + code)

    # 拆分表
    if fulllist:
        print("Generating radical table")
        with open('../' + folder + '/radical_flypy.dict.yaml', 'r') as f:
            for l in f:
                matches = re.findall(r'(\w+)\t([a-z]+)', l)
                if not matches: continue
                char, code = matches[0]
                table.add(char, 'ocz' + code)

    # 补充表
    if fulllist:
        print("Generating extended table")
        directory = '../' + folder + '/' + extended + '/'
        for filename in os.listdir(directory):
            if "tencent" in filename:
                continue
            filepath = os.path.join(directory, filename)
            with open(filepath, 'r') as f:
                for l in f:
                    matches = re.findall(r'[a-z]{2};[a-z]{2}', l)
                    if not matches: continue
                    parts = l.split('\t')
                    word = parts[0]
                    codes = parts[1]

                    pairs = codes.split()
                    parts_before_semicolon = [pair.split(';')[0] for pair in pairs]

                    code = ''.join(parts_before_semicolon)
                    table.add(word, code)


    with open(output, 'w') as f:
        table.print_c2w(f)
        # table.print_w2c(f)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder', default='molong-chs', help='方案文件夹')
    parser.add_argument('--extended', default='snow-dicts', help='补充文件夹')
    parser.add_argument('--output', default='dazhu.txt', help='输出文件')
    parser.add_argument('-f', '--fulllist', action='store_true', help='输出全表')
    parser.add_argument('--opencc', '-c',
                        default='moran_t2s.json',
                        help='轉換詞表（空表示不轉換）')
    args = parser.parse_args()
    main(args)
