(function extractPlaylist() {
    // 等待页面完全加载
    if (document.readyState !== 'complete') {
        console.log('⏳ 页面尚未完全加载，请稍后重试');
        return;
    }

    // 尝试从 iframe 中获取内容
    let doc = document;
    const iframe = document.getElementById('g_iframe');
    if (iframe && iframe.contentDocument) {
        try {
            if (iframe.contentDocument.readyState === 'complete' || iframe.contentDocument.readyState === 'interactive') {
                doc = iframe.contentDocument;
                console.log('🔍 使用 iframe 文档');
            }
        } catch (e) {}
    }

    // 定位歌曲行
    let rows = doc.querySelectorAll('tr[data-res-id]');
    if (!rows.length) {
        // 尝试其他选择器
        const plyElements = doc.querySelectorAll('.ply');
        if (plyElements.length) {
            rows = Array.from(plyElements).map(el => el.closest('tr')).filter(Boolean);
        }
    }
    if (!rows.length) {
        const numElements = doc.querySelectorAll('.num');
        if (numElements.length) {
            rows = Array.from(numElements).map(el => el.closest('tr')).filter(Boolean);
        }
    }
    if (!rows.length) {
        const anchors = doc.querySelectorAll('a[href*="/song?id="]');
        if (anchors.length) {
            rows = Array.from(anchors).map(a => a.closest('tr')).filter(Boolean);
        }
    }

    if (!rows || !rows.length) {
        console.log('❌ 未找到歌曲列表，请确认当前页面是歌单详情页');
        return;
    }

    // 去重
    const seenIds = new Set();
    const uniqueRows = [];
    rows.forEach(row => {
        let id = row.getAttribute('data-res-id');
        if (!id) {
            const title = row.querySelector('b')?.textContent?.trim() || row.querySelector('a[href*="/song?id="]')?.textContent?.trim() || '';
            const artist = row.querySelector('td:nth-child(4) span[title]')?.getAttribute('title') || '';
            id = title + '|||' + artist;
        }
        if (id && !seenIds.has(id)) {
            seenIds.add(id);
            uniqueRows.push(row);
        }
    });

    console.log(`🔍 共找到 ${uniqueRows.length} 首歌曲`);

    const songs = [];
    uniqueRows.forEach(row => {
        // 歌名：使用多种方法
        let title = '';
        // 优先找 <b> 标签（包含歌名）
        const bTag = row.querySelector('b');
        if (bTag) {
            title = bTag.textContent.trim();
            // 如果 title 中包含乱码（可能是混淆），可以尝试从 <a> 或 <span> 获取纯净标题
            // 但 textContent 已经合并了所有子节点，应该没问题。
        }
        if (!title) {
            const aTag = row.querySelector('a[href*="/song?id="]');
            if (aTag) title = aTag.textContent.trim();
        }
        if (!title) {
            const ttc = row.querySelector('.ttc');
            if (ttc) title = ttc.textContent.trim();
        }
        // 清理多余空格和换行
        title = title.replace(/\s+/g, ' ').trim();
        if (!title) return;

        // 艺术家：优先使用 title 属性（通常最干净）
        let artist = '';
        // 方法1：查找 td 中的 span[title]
        const artistSpan = row.querySelector('td:nth-child(4) span[title]');
        if (artistSpan) {
            artist = artistSpan.getAttribute('title').trim();
        } else {
            // 方法2：查找所有艺术家链接
            const artistLinks = row.querySelectorAll('td:nth-child(4) a');
            if (artistLinks.length) {
                artist = Array.from(artistLinks).map(a => a.textContent.trim()).join(' / ');
            } else {
                // 方法3：从 data-res-author 获取
                const dataElem = row.querySelector('[data-res-author]');
                if (dataElem) artist = dataElem.getAttribute('data-res-author').trim();
            }
        }
        if (!artist) artist = '未知歌手';

        songs.push({ title, artist });
    });

    if (!songs.length) {
        console.log('❌ 未提取到有效歌曲信息');
        return;
    }

    // 去重（歌名+艺术家）
    const seen = new Set();
    const unique = songs.filter(s => {
        const key = `${s.title}|||${s.artist}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
    });

    console.log(`✅ 共提取 ${unique.length} 首歌曲（已去重，原${songs.length}首）`);
    console.log('📋 文字版歌单如下（可复制）：\n');
    const text = unique.map((s, i) => `${String(i+1).padStart(3, ' ')}. ${s.title} - ${s.artist}`).join('\n');
    console.log(text);
    console.log('\n📋 仅歌名列表：\n');
    const names = unique.map((s, i) => `${String(i+1).padStart(3, ' ')}. ${s.title}`).join('\n');
    console.log(names);
    console.log('💡 请手动选中上方文本复制');
})();