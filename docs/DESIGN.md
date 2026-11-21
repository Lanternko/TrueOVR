# Design

## Scene

玩家在桌面螢幕持續觀賽。低亮度深灰外框、木色全場與琥珀／青色兩隊，讓視線集中在球與人物。

## Layout

桌面 broadcast 為 16:9，比分置頂；左右各五張真人頭像，中央球場；一句播報與播放控制置底。完整事件紀錄與 box score 按需展開。

## Motion

球、人物、球網與統計結算共用事件時間軸。肢體、位移及拋物線傳遞事件資訊；不用獨立剪影或長橫幅。動態只操作 transform、SVG 關節與 opacity。

## Identity

主隊琥珀、客隊青色；場上通用人物使用隊色球衣、姓名與陣容編號。真人頭像置於側欄。球員外貌與正式球衣尚待獨立美術階段。

## Typography and inclusion

Segoe UI / Microsoft JhengHei 系統字體。比分與時間使用等寬數字。所有播放及選人控制支援鍵盤焦點，尊重 prefers-reduced-motion，390px 窄螢幕重排控制列。
