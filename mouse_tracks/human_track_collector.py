import json

from playwright.sync_api import sync_playwright


def human_track_collector():
    tracks = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://你的目标网站.com")  # 替换为包含滑块的页面

        print("请在浏览器中手动拖拽滑块，完成后按回车保存...")

        # 注入监听器，捕获 mousedown 到 mouseup 之间的所有 mousemove
        page.evaluate("""() => {
            window.__track_data = [];
            let isDragging = false;
            document.addEventListener('mousedown', () => { isDragging = true; });
            document.addEventListener('mouseup', () => { isDragging = false; });
            document.addEventListener('mousemove', (e) => {
                if (isDragging) {
                    window.__track_data.push({
                        x: e.clientX,
                        y: e.clientY,
                        ts: Date.now()
                    });
                }
            });
        }""")

        input()  # 阻塞等待手动操作
        data = page.evaluate("window.__track_data")
        tracks.append(data)
        browser.close()

    # 保存轨迹
    with open("human_tracks_cdp.json", "w") as f:
        json.dump(tracks, f)
    print(f"成功采集 {len(tracks)} 条真实轨迹！")


if __name__ == "__main__":
    human_track_collector()
