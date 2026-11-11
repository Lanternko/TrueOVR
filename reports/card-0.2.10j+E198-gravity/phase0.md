# E-198 phase0（跑 KG 前；只用 KAU）

- 人群：卡片 MIN≥500 且 2025-26 本季 RAPM poss≥1000，379 人；接球射手組（KAU long≥75 且 creation≤60）29 人。
- KAU ranking.csv sha256 `8b3e99d682ad6d7e4b5c5068f3d0d88e484ef0754af4fe789aae323e9a1c6c34`（＝card-0.2.10i）。bootstrap 球員層 2000 次，seed 20261102。
- KAU 全體 Spearman(OVR, 本季 RAPM) = 0.5876，90% 半寬 **h = 0.0580** → 沒弄壞門檻：ρ_KG − ρ_KAU ≥ **-0.1160**。
- 接球射手組平均名次殘差（pct RAPM − pct OVR，正＝低估）= +11.97 點，**MDE_rank = 8.26** 點。
- 接球射手組平均價值殘差（z RAPM − b·z OVR，b=0.613）= +0.2631 SD，**MDE_value = 0.2335** SD。
- 組平均 pct(OVR) = 43.0。假象規則（寫檔前定）：偏離 50 超過 10 點 → 名次殘差有均值回歸假象，A 以價值殘差判；
  否則以名次殘差判（價值殘差只報告）。本次：**無假象，A 主口徑＝名次殘差**。
- A 判定式：縮小量＝sign(KAU 組平均)·(KAU − KG) ≥ MDE（主口徑）。
- 分半（單雙場）KAU 點估計：odd ρ 0.4892、組名次殘差 +15.48、價值殘差 +0.3877；
  even ρ 0.5079、組名次殘差 +9.65、價值殘差 +0.1319。
- 組員：Al Horford、Nicolas Batum、Harrison Barnes、Gary Harris、Myles Turner、Royce O'Neale、Taurean Prince、John Collins、Duncan Robinson、Grant Williams、Aaron Nesmith、Josh Green、Sam Merrill、Vít Krejčí、Moses Moody、Davion Mitchell、Luka Garza、Sam Hauser、Micah Potter、Jaylin Williams、Keon Ellis、Josh Minott、Baylor Scheierman、Pete Nance、AJ Green、Ja'Kobe Walter、Jaylon Tyson、Jamison Battle、Kasparas Jakučionis
