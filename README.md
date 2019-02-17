# aiopixiv3
この子をaiohttpを使って書き換えたもの。
https://github.com/upbit/pixivpy

# 特徴
async with を使うとセッションを自動で閉じる。

```py
import aiopixiv3
async with aiopixiv3.AppPixivAPI() as api:
    pass
```
