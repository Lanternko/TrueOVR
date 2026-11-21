# E-089 比對：inseason 0.2.1（out-022）→ inseason 0.2.2（out-024）

同一份資料（cutoff 2026-10-28），368 人。|ΔOVR| 中位數 **2.80**、平均 3.39、最大 15.80；>5 分 67 人、>10 分 15 人；ΔOVR 有號中位數 +1.10。拆解重現檢查最大差 5.33e-02。

## 前 20 名進出

| 方向 | 球員 | OVR（該版） | 名次（該版） | 名次（另一版） | OVR（另一版） |
|---|---|---|---|---|---|
| 進 | Dylan Harper | 90.5 | 20 | 30 | 85.7 |
| 出 | Lauri Markkanen | 88.1 | 20 | 21 | 90.3 |

新版前 20：Shai Gilgeous-Alexander 105.8、Luka Dončić 104.9、Nikola Jokić 103.9、Franz Wagner 100.1、Victor Wembanyama 99.9、Amen Thompson 96.8、Derrick White 95.4、Chet Holmgren 94.4、Cade Cunningham 94.1、Joel Embiid 93.9、Giannis Antetokounmpo 93.9、Jamal Murray 93.8、Donovan Mitchell 93.7、Tyrese Maxey 93.3、Kawhi Leonard 92.5、Jayson Tatum 91.8、OG Anunoby 91.6、Evan Mobley 91.4、Kevin Durant 90.6、Dylan Harper 90.5

舊版前 20：Nikola Jokić 106.1、Shai Gilgeous-Alexander 105.0、Luka Dončić 102.8、Franz Wagner 99.2、Derrick White 97.5、Giannis Antetokounmpo 96.0、Joel Embiid 95.2、Victor Wembanyama 95.0、Kawhi Leonard 94.8、Chet Holmgren 93.6、Kevin Durant 91.1、Cade Cunningham 91.0、Donovan Mitchell 90.6、Jamal Murray 89.4、Amen Thompson 89.0、OG Anunoby 88.5、Tyrese Maxey 88.4、Evan Mobley 88.3、Jayson Tatum 88.2、Lauri Markkanen 88.1

## ΔOVR 最大 10 人

| 球員 | 隊 | N | 年齡 | 舊 OVR | 新 OVR | Δ | 舊 MPG0 | mpgAvail(新) | 錨點 | 用人項 | MPG0 | 主因 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Paolo Banchero | ORL | 2 | 23 | 59.8 | 75.6 | +15.8 | 34.8 | 34.8 | -8.9 | +24.8 | +0.0 | 用人項 |
| Keyonte George | UTA | 5 | 22 | 64.6 | 49.0 | -15.6 | 33.1 | 33.1 | -7.3 | -8.4 | +0.0 | 用人項 |
| Jaylen Wells | MEM | 4 | 22 | 70.7 | 55.7 | -15.0 | 26.4 | 26.4 | -3.4 | -11.6 | +0.0 | 用人項 |
| Alex Sarr | WAS | 5 | 21 | 69.7 | 55.3 | -14.4 | 27.2 | 27.2 | -3.8 | -10.6 | +0.0 | 用人項 |
| Kyshawn George | WAS | 5 | 22 | 75.1 | 60.9 | -14.2 | 29.0 | 29.0 | -0.1 | -14.0 | +0.0 | 用人項 |
| Reed Sheppard | HOU | 4 | 22 | 53.0 | 66.7 | +13.7 | 26.2 | 26.2 | -7.9 | +21.6 | +0.0 | 用人項 |
| Cooper Flagg | DAL | 4 | 19 | 78.0 | 64.6 | -13.4 | 33.5 | 33.5 | +1.6 | -15.0 | +0.0 | 用人項 |
| Cedric Coward | MEM | 3 | 22 | 75.1 | 61.9 | -13.2 | 25.8 | 25.8 | +0.3 | -13.4 | +0.0 | 用人項 |
| Egor Dëmin | BKN | 4 | 20 | 68.4 | 55.5 | -12.9 | 25.2 | 25.2 | -3.4 | -9.6 | +0.0 | 用人項 |
| Ace Bailey | UTA | 5 | 19 | 61.0 | 48.1 | -12.9 | 27.6 | 27.6 | -7.3 | -5.6 | +0.0 | 錨點 |

（錨點／用人項／MPG0 三欄依序疊加，加總＝Δ；用人項含 predNew 對 p 的整體縮放與 L、a、y、v、d 各項。）

## 年齡

| 組 | 人數 | ΔOVR 中位數 |
|---|---|---|
| young<=23 | 98 | +1.10 |
| old>=31 | 54 | -0.60 |
| mid | 216 | +1.60 |
| noAge | 0 | — |

各項貢獻中位數（有號／絕對值）：dAnchors -1.97／3.31；dUsage +1.59／3.38；dMpg +0.00／0.00

## MPG0 口徑差（|mpgAvail − 舊 MPG0|）

- 賽季榜 368 人：> 3 的 81 人，中位數 0.00。最大 5 人：Daeqwon Plowden（舊 26.4→新 10.6，OVR -3.9）；DeAndre Jordan（舊 16.6→新 2.5，OVR -4.2）；Chaney Johnson（舊 20.4→新 6.6，OVR -8.5）；Elijah Harkless（舊 20.9→新 7.3，OVR -3.2）；Bogdan Bogdanović（舊 19.6→新 7.8，OVR -4.3）
- 卡內 582 人：> 3 的 205 人。最大 5 人：Josh Oduro（舊 27.26→新 4.3）；Daeqwon Plowden（舊 26.39→新 10.55）；Keshon Gilbert（舊 18.45→新 3.21）；DeAndre Jordan（舊 16.57→新 2.45）；Chaney Johnson（舊 20.45→新 6.56）

## (c2)

- OVR/lastOVR/predNew/g 全有限：True；人數 368→368，名單相同：True
- f=0、k 上界檢查 (a)（t1）最大差 0.0444（<0.5）
- lastOVR 對 card 0.2.4 ranking.csv ovr（368 人同名配對）：Spearman 0.999994；最大差 0.10（差 >0.1 的 0 人）
- 差最大 10 人：Tristan da Silva 65.8 vs 65.9；Scottie Barnes 90.4 vs 90.3；Myles Turner 77.8 vs 77.9；Kentavious Caldwell-Pope 71.2 vs 71.1；Herbert Jones 89.9 vs 89.8；Domantas Sabonis 74.4 vs 74.3；Daniel Gafford 74.3 vs 74.4；Bam Adebayo 86.6 vs 86.7；Yves Missi 48.0 vs 48.1；Kyle Filipowski 51.0 vs 50.9
