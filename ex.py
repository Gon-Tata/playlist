#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import re
import hashlib
from pathlib import Path
from mutagen import File
from mutagen.id3 import ID3, APIC, TIT2, TPE1
from mutagen.mp3 import MP3

# ========== 配置 ==========
MUSIC_DIR = "CloudMusic"
COVERS_DIR = "covers"
OUTPUT_JSON = "playlist.json"
COVER_SIZE_LIMIT = 2 * 1024 * 1024
PLAYLIST_FILE = "pll.md"

# ========== 辅助函数 ==========
def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)

def safe_filename(name):
    invalid_chars = '<>:"/\\|?*'
    for ch in invalid_chars:
        name = name.replace(ch, '_')
    return name.strip()

def get_cover_extension(pic_data, mime):
    if mime == 'image/jpeg':
        return '.jpg'
    elif mime == 'image/png':
        return '.png'
    elif mime == 'image/gif':
        return '.gif'
    elif mime == 'image/webp':
        return '.webp'
    else:
        if pic_data[:4] == b'\x89PNG':
            return '.png'
        elif pic_data[:2] == b'\xFF\xD8':
            return '.jpg'
        elif pic_data[:3] == b'GIF':
            return '.gif'
        else:
            return '.jpg'

def extract_cover(mp3_path, idx, hash_val):
    try:
        audio = MP3(mp3_path, ID3=ID3)
        if audio.tags is None:
            return None
        for tag in audio.tags.values():
            if isinstance(tag, APIC):
                pic_data = tag.data
                if not pic_data or len(pic_data) > COVER_SIZE_LIMIT:
                    continue
                ext = get_cover_extension(pic_data, tag.mime)
                cover_filename = f"{idx:04d}_{hash_val}{ext}"
                cover_path = os.path.join(COVERS_DIR, cover_filename)
                ensure_dir(COVERS_DIR)
                with open(cover_path, 'wb') as f:
                    f.write(pic_data)
                return os.path.join(COVERS_DIR, cover_filename).replace('\\', '/')
    except Exception as e:
        print(f"  ⚠️ 提取封面失败: {e}")
    return None

def md5_file(filepath):
    try:
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()[:8]
    except FileNotFoundError:
        print(f"⚠️ 文件不存在: {filepath}")
        return None

def normalize_text(text):
    if not text:
        return ""
    text = str(text)
    text = text.lower()
    fullwidth_map = {
        'ａ': 'a', 'ｂ': 'b', 'ｃ': 'c', 'ｄ': 'd', 'ｅ': 'e',
        'ｆ': 'f', 'ｇ': 'g', 'ｈ': 'h', 'ｉ': 'i', 'ｊ': 'j',
        'ｋ': 'k', 'ｌ': 'l', 'ｍ': 'm', 'ｎ': 'n', 'ｏ': 'o',
        'ｐ': 'p', 'ｑ': 'q', 'ｒ': 'r', 'ｓ': 's', 'ｔ': 't',
        'ｕ': 'u', 'ｖ': 'v', 'ｗ': 'w', 'ｘ': 'x', 'ｙ': 'y',
        'ｚ': 'z',
        'Ａ': 'a', 'Ｂ': 'b', 'Ｃ': 'c', 'Ｄ': 'd', 'Ｅ': 'e',
        'Ｆ': 'f', 'Ｇ': 'g', 'Ｈ': 'h', 'Ｉ': 'i', 'Ｊ': 'j',
        'Ｋ': 'k', 'Ｌ': 'l', 'Ｍ': 'm', 'Ｎ': 'n', 'Ｏ': 'o',
        'Ｐ': 'p', 'Ｑ': 'q', 'Ｒ': 'r', 'Ｓ': 's', 'Ｔ': 't',
        'Ｕ': 'u', 'Ｖ': 'v', 'Ｗ': 'w', 'Ｘ': 'x', 'Ｙ': 'y',
        'Ｚ': 'z',
        '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
        '５': '5', '６': '6', '７': '7', '８': '8', '９': '9',
        '（': '(', '）': ')', '　': ' ', '・': '·', '〜': '~',
        '～': '~',
    }
    for fw, hw in fullwidth_map.items():
        text = text.replace(fw, hw)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def normalize_title(title):
    if not title:
        return ""
    title = re.sub(r'[（(][^）)]*[）)]', '', title)
    return normalize_text(title)

def parse_playlist_from_md(md_path):
    if not os.path.exists(md_path):
        print(f"❌ 歌单文件 {md_path} 不存在")
        return []
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    songs = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        pattern = r'^\s*(\d+)\.\s+(.+?)\s*-\s*(.+)$'
        match = re.match(pattern, line)
        if not match:
            pattern2 = r'^(.+?)\s*-\s*(.+)$'
            match2 = re.match(pattern2, line)
            if match2:
                title = match2.group(1).strip()
                artist = match2.group(2).strip()
                songs.append((None, title, artist))
            else:
                songs.append((None, line, "未知歌手"))
        else:
            idx = int(match.group(1))
            title = match.group(2).strip()
            artist = match.group(3).strip()
            songs.append((idx, title, artist))
    if songs and songs[0][0] is not None:
        songs.sort(key=lambda x: x[0])
    print(f"✅ 从 {md_path} 解析到 {len(songs)} 首歌曲")
    return songs

def get_local_info(mp3_path):
    try:
        audio = MP3(mp3_path, ID3=ID3)
        tags = audio.tags
        title = None
        artist = None
        if tags:
            title = str(tags.get('TIT2') or tags.get('TT2'))
            artist = str(tags.get('TPE1') or tags.get('TP1'))
        if not title or not artist:
            basename = os.path.basename(mp3_path)
            name = os.path.splitext(basename)[0]
            if ' - ' in name:
                parts = name.split(' - ', 1)
                title = parts[0].strip()
                artist = parts[1].strip() if len(parts) > 1 else "未知歌手"
            else:
                title = name.strip()
                artist = "未知歌手"
    except Exception as e:
        print(f"  ⚠️ 读取文件失败: {mp3_path}, {e}")
        return None
    if not title:
        title = os.path.splitext(os.path.basename(mp3_path))[0]
        artist = "未知歌手"
    title = title.strip()
    artist = artist.strip() if artist else "未知歌手"
    norm_title = normalize_title(title)
    norm_artist = normalize_text(artist)
    return {
        'title': title,
        'artist': artist,
        'norm_title': norm_title,
        'norm_artist': norm_artist,
        'key': (norm_title, norm_artist)
    }

def match_songs(local_files, playlist_songs):
    local_map = {}
    local_titles = {}
    for mp3_path in local_files:
        info = get_local_info(mp3_path)
        if info:
            key = info['key']
            if key not in local_map:
                local_map[key] = mp3_path
            norm_title = info['norm_title']
            if norm_title not in local_titles:
                local_titles[norm_title] = []
            local_titles[norm_title].append((mp3_path, info['norm_artist']))

    matched = []
    unmatched_count = 0
    for idx, title, artist in playlist_songs:
        norm_title = normalize_title(title)
        norm_artist = normalize_text(artist)
        key = (norm_title, norm_artist)

        if key in local_map:
            matched.append((idx, local_map[key]))
            continue

        if norm_title in local_titles:
            candidates = local_titles[norm_title]
            if len(candidates) == 1:
                matched.append((idx, candidates[0][0]))
                continue
            else:
                for path, art in candidates:
                    if norm_artist in art or art in norm_artist:
                        matched.append((idx, path))
                        break
                else:
                    matched.append((idx, candidates[0][0]))
                    print(f"  ⚠️ 模糊匹配: 歌单 '{title}' → 本地 '{os.path.basename(candidates[0][0])}'")
                continue

        stripped_title = re.sub(r'[（(][^）)]*[）)]', '', norm_title).strip()
        if stripped_title and stripped_title != norm_title:
            found = False
            for local_key, path in local_map.items():
                local_stripped = re.sub(r'[（(][^）)]*[）)]', '', local_key[0]).strip()
                if local_stripped == stripped_title:
                    if norm_artist in local_key[1] or local_key[1] in norm_artist:
                        matched.append((idx, path))
                        found = True
                        break
            if not found:
                for local_key, path in local_map.items():
                    local_stripped = re.sub(r'[（(][^）)]*[）)]', '', local_key[0]).strip()
                    if local_stripped == stripped_title:
                        matched.append((idx, path))
                        print(f"  ⚠️ 模糊匹配(去除括号): 歌单 '{title}' → 本地 '{os.path.basename(path)}'")
                        found = True
                        break
            if not found:
                unmatched_count += 1
        else:
            unmatched_count += 1

    print(f"✅ 成功匹配 {len(matched)} 首歌曲，未匹配 {unmatched_count} 首")
    return matched

def main():
    print("🎵 歌单排序脚本启动（读取 pll.md）")

    playlist_songs = parse_playlist_from_md(PLAYLIST_FILE)
    if not playlist_songs:
        return

    ensure_dir(MUSIC_DIR)
    local_mp3s = [p.resolve() for p in Path(MUSIC_DIR).glob('**/*.mp3')]
    if not local_mp3s:
        print("❌ 未在 music/ 目录找到任何 MP3 文件")
        return
    print(f"📁 找到 {len(local_mp3s)} 个本地 MP3 文件")

    matched = match_songs(local_mp3s, playlist_songs)
    if not matched:
        print("❌ 没有匹配到任何歌曲，请检查文件名或 ID3 标签是否与歌单一致")
        return

    playlist_data = []
    for order, mp3_path in matched:
        hash_val = md5_file(mp3_path)
        if hash_val is None:
            print(f"❌ 跳过文件 {mp3_path}（无法计算哈希）")
            continue

        new_mp3_name = f"{order:04d}_{hash_val}.mp3"
        new_mp3_path = os.path.join(os.path.dirname(mp3_path), new_mp3_name)

        if os.path.basename(mp3_path) != new_mp3_name:
            try:
                os.rename(mp3_path, new_mp3_path)
                print(f"✅ 重命名 MP3: {os.path.basename(mp3_path)} → {new_mp3_name}")
                mp3_path = new_mp3_path
            except Exception as e:
                print(f"❌ 重命名失败: {e}")
                continue

        cover_rel = extract_cover(mp3_path, order, hash_val)

        info = get_local_info(mp3_path)
        if info:
            title = info['title']
            artist = info['artist']
        else:
            title = os.path.splitext(os.path.basename(mp3_path))[0]
            artist = "未知歌手"

        # ========== 修改点：将 src 保存为相对路径 ==========
        # 获取相对于当前工作目录的相对路径
        rel_path = os.path.relpath(mp3_path, start=os.getcwd())
        # 统一使用 / 作为路径分隔符
        src = rel_path.replace('\\', '/')

        playlist_data.append({
            "title": title,
            "artist": artist,
            "src": src,
            "cover": cover_rel
        })

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(playlist_data, f, ensure_ascii=False, indent=2)
    print(f"✅ 生成 {OUTPUT_JSON}，共 {len(playlist_data)} 首歌曲")

    matched_paths = set(p[1] for p in matched)
    unmatched_local = [p for p in local_mp3s if p not in matched_paths]
    if unmatched_local:
        print(f"⚠️ 以下本地文件未在歌单中找到匹配，已忽略：")
        for p in unmatched_local:
            print(f"   {os.path.basename(p)}")

if __name__ == "__main__":
    main()