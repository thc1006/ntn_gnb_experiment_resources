# 5G NTN 實驗專案準備指南

## 專案概述
- **實驗目標**：透過 USRP-2953R(X310) 發射 FR1 L-band (n8頻段) 30MHz 訊號，經由 ITRI channel emulator，最終由 B210 接收
- **當前日期**：2025年11月18日
- **場景假設**：GEO 衛星通訊，避免都卜勒位移

## 一、ITRI Channel Emulator 型號分析

### 最可能的型號選項

#### 1. **Keysight PROPSIM 系列（最高可能性）**
根據最新資訊，ITRI 在多個 5G NTN 專案中與 Keysight 有緊密合作關係：

**S8825A Satellite and Aerospace Channel Emulation Toolset**
- **頻率範圍**：支援 L-band、S-band、C-band、X-band、Ku-band、K-band
- **特別支援**：5G NTN Release 17/19 specifications
- **核心硬體**：基於 PROPSIM F64 或 FS16
- **關鍵功能**：
  - 支援 GEO/LEO/MEO 軌道模擬
  - 長延遲處理（GEO 場景約 250ms）
  - 都卜勒效應模擬
  - 多路徑衰落模擬
  - 支援 FR1 頻段（包括 n8 L-band）

**PROPSIM F64**
- 最多 64 個衰落通道
- 頻寬：最高 800 MHz
- 延遲：最長 2秒（適合 GEO）
- 都卜勒：±1.2 MHz

**PROPSIM FS16**
- 最多 16 個衰落通道  
- 頻寬：最高 160 MHz
- 延遲：最長 400ms（適合 GEO）
- 成本較低的選項

#### 2. **Spirent Vertex 系列**（次要可能性）
注意：2025年10月 Spirent 已被 Keysight 收購，channel emulation 業務轉給 Viavi

**Spirent Vertex Channel Emulator**
- 支援 3GPP TR 38.811 NTN channel models
- L-band 支援能力
- GEO satellite channel modeling
- 但因收購案可能供貨有變動

#### 3. **Rohde & Schwarz CMX500**（可能性較低）
- 主要用於終端測試而非系統級測試
- 支援 NTN 測試但功能較侷限

### ITRI 的實際選擇傾向
根據公開資訊，ITRI 在以下專案中的設備選擇：
- 與 MediaTek、Eutelsat 合作：使用 Rohde & Schwarz 測試設備
- 內部開發：ITRI 自行開發 NR-NTN gNB (Ameba RAN)
- **Channel Emulator**：最可能採用 Keysight PROPSIM 系列

## 二、硬體規格建議

### 第三台主機規格（連接 B210）

#### 最低規格
- **CPU**：Intel Core i5-10400 或 AMD Ryzen 5 5600X（6核心）
- **RAM**：16GB DDR4 3200MHz
- **儲存**：512GB NVMe SSD
- **USB**：USB 3.0/3.1 Gen1 ports（至少2個）
- **網路**：Gigabit Ethernet
- **作業系統**：Ubuntu 22.04 LTS 或 24.04 LTS

#### 建議規格
- **CPU**：Intel Core i7-12700K 或 AMD Ryzen 7 5800X（8核心）
- **RAM**：32GB DDR4 3200MHz（雙通道）
- **儲存**：1TB NVMe SSD + 2TB HDD（資料儲存）
- **USB**：USB 3.1 Gen2 或 USB 3.2 ports（至少4個）
- **網路**：2.5 Gigabit Ethernet
- **GPU**：NVIDIA GTX 1660 或以上（用於訊號處理加速）
- **電源**：650W 80+ Gold 認證

#### 關鍵考量
- **USB 頻寬**：B210 需要穩定的 61.44MS/s 取樣率
- **CPU 效能模式**：設定為 performance governor
- **即時核心**：考慮安裝 low-latency 或 real-time kernel
- **散熱**：良好的散熱系統避免 thermal throttling

### 專案負責人筆電規格（2025年推薦）

#### 高階工作站筆電推薦
**Dell Precision 5680 或 HP ZBook Studio G10**
- **CPU**：Intel Core i9-13900HX 或 AMD Ryzen 9 7945HX
- **RAM**：64GB DDR5 5600MHz（可擴充至128GB）
- **儲存**：2TB PCIe Gen4 NVMe SSD
- **GPU**：NVIDIA RTX 4070 或 RTX A3000（8GB VRAM）
- **顯示**：16" 4K OLED，100% DCI-P3
- **連接埠**：
  - 2x Thunderbolt 4/USB4
  - 2x USB-A 3.2 Gen2
  - HDMI 2.1
  - SD card reader
  - RJ45 Ethernet（2.5GbE）
- **電池**：90Wh 以上
- **重量**：< 2.5kg

#### 替代選項（較輕便）
**Lenovo ThinkPad P16s Gen 2 或 ASUS ProArt Studiobook 16**
- **CPU**：Intel Core i7-1360P 或 AMD Ryzen 7 PRO 7840U
- **RAM**：32GB LPDDR5
- **儲存**：1TB PCIe Gen4 SSD
- **GPU**：NVIDIA RTX 4050（6GB）
- **重量**：< 2kg

## 三、對接前準備實驗方案

### 實驗一：端對端連通性測試
**目的**：驗證 X310 → B210 直接連接
1. **配置**：
   - X310 和 B210 透過 30dB 衰減器直接連接
   - 發射功率：-20dBm
   - 頻率：1.8GHz（n8 band 中心頻率）
   - 頻寬：30MHz
2. **驗證項目**：
   - EVM < 8%
   - 訊號強度穩定性
   - IQ constellation 正確性

### 實驗二：訊號衰減模擬
**目的**：模擬 GEO 路徑損耗
1. **配置**：
   - 使用多級衰減器串接（總計約 190dB path loss）
   - 加入 LNA 補償
2. **測試項目**：
   - 最低可解調 SNR
   - 動態範圍測試

### 實驗三：延遲容忍度測試
**目的**：驗證系統對 GEO 延遲的處理
1. **方法**：
   - 軟體延遲注入（約 250ms RTT）
   - 使用 tc (traffic control) 工具
2. **驗證**：
   - HARQ timing 調整
   - TA (Timing Advance) 計算

### 實驗四：頻率穩定度測試
**目的**：確保頻率同步
1. **使用 GPSDO**：
   - X310 內建 GPSDO
   - B210 外接 10MHz reference
2. **測量**：
   - 載波頻率偏移 < 0.01 ppm
   - 相位雜訊測量

### 實驗五：Channel Emulator 介面驗證
**目的**：熟悉可能的介面配置
1. **RF 介面檢查**：
   - 連接器類型（N-type、SMA）
   - 阻抗匹配（50Ω）
   - 最大輸入功率限制
2. **控制介面**：
   - LAN/USB 控制連接
   - SCPI 命令測試
   - 預設 channel model 載入

## 四、必要測試設備清單

### 核心測試設備
1. **頻譜分析儀**
   - 頻率範圍：至少到 3GHz
   - RBW：1Hz - 1MHz
   - 建議：
     - 高階：Keysight N9320B、Rohde & Schwarz FSW
     - 中階：Rigol DSA815-TG、Siglent SSA3032X
     - 入門：TinySA Ultra（$150）

2. **RF 射頻訊號遮蔽箱**
   - 尺寸：至少 60x40x30 cm
   - 屏蔽效能：> 80dB @ 2GHz
   - 建議：JRE Test Enclosure 或 Ramsey STE3000

3. **功率計**
   - 頻率範圍：100MHz - 6GHz
   - 動態範圍：-50dBm to +20dBm
   - 建議：Mini-Circuits PWR-6GHS

4. **向量網路分析儀（VNA）**
   - 用於 S-parameter 測量
   - 建議：NanoVNA V2（便宜）或 Keysight E5071C

### 輔助設備
1. **衰減器組**
   - 固定：3dB、6dB、10dB、20dB、30dB
   - 可變：0-60dB programmable attenuator
   - 功率承受：至少 2W

2. **RF 線纜與轉接頭**
   - SMA 線纜：多條不同長度（0.5m、1m、2m）
   - 轉接頭：SMA-N、SMA-BNC、N-BNC
   - 品質：低損耗（< 1dB/m @ 2GHz）

3. **濾波器**
   - Band-pass filter：1.7-1.9 GHz（n8 band）
   - Low-pass filter：2.5GHz cutoff
   - 用於抑制諧波和雜散

4. **放大器**
   - LNA：NF < 1dB，Gain 20dB
   - Power Amplifier：如需要，+30dBm output

### 安全防護設備
1. **個人防護**
   - RF 輻射檢測器
   - 警示標誌
   - **注意**：L-band 功率密度應 < 10 W/m²（公眾暴露限值）
   - 一般實驗室環境不需要鉛衣或特殊護目鏡

2. **設備保護**
   - 限幅器（Limiter）：保護接收端
   - DC Block：防止直流損壞
   - 接地帶：防止靜電

### 軟體工具
1. **SDR 軟體**
   - GNU Radio（已確認支援）
   - srsRAN NTN
   - OpenAirInterface NTN
   - UHD (USRP Hardware Driver)

2. **分析工具**
   - MATLAB/Octave（訊號分析）
   - Wireshark（協議分析）
   - IQ分析工具

3. **Channel Emulator 控制軟體**
   - Keysight PROPSIM Control Software
   - Python SCPI library

## 五、對接日準備檢查清單

### 前一週
- [ ] 確認 ITRI channel emulator 具體型號
- [ ] 取得設備操作手冊
- [ ] 準備所有 RF 線纜和轉接頭
- [ ] 完成所有預備實驗
- [ ] 準備測試腳本和自動化程序

### 前一天
- [ ] 檢查所有設備電源
- [ ] 確認網路連接（SSH、VPN）
- [ ] 備份現有配置
- [ ] 準備問題排查流程圖
- [ ] 團隊分工確認

### 對接當天
- [ ] 設備預熱（30分鐘）
- [ ] 頻率校準確認
- [ ] 功率等級確認（避免超過 channel emulator 輸入限制）
- [ ] 即時監控準備
- [ ] 記錄表格準備

## 六、潛在問題與解決方案

### 問題1：功率匹配
- **問題**：Channel emulator 輸入功率限制
- **解決**：使用可調衰減器，預設 -10dBm 輸入

### 問題2：阻抗不匹配
- **問題**：反射造成訊號品質下降
- **解決**：使用 VNA 預先測量，必要時加入匹配網路

### 問題3：時鐘同步
- **問題**：頻率偏移導致解調失敗
- **解決**：確保所有設備使用同一 10MHz reference

### 問題4：延遲補償
- **問題**：GEO 延遲超過系統預設值
- **解決**：修改 MAC layer timing parameters

## 七、專案時程建議

### Phase 1：準備階段（2週）
- Week 1：設備採購與環境搭建
- Week 2：基礎功能驗證

### Phase 2：預實驗階段（2週）
- Week 3：端對端測試
- Week 4：參數優化

### Phase 3：對接準備（1週）
- 與 ITRI 確認介面規格
- 最終測試與調校

### Phase 4：正式對接
- 預留 2-3 天進行現場調試

## 八、預算估算

### 必要設備（約 USD）
- 頻譜分析儀：$3,000-30,000
- RF 遮蔽箱：$2,000-5,000
- 衰減器/濾波器組：$1,000
- RF 線纜配件：$500
- 功率計：$2,000

### 選配設備
- VNA：$50-50,000（視規格）
- 高階示波器：$10,000+

### 總預算範圍
- 基礎配置：$10,000-20,000
- 完整配置：$30,000-100,000

## 九、聯絡資訊與資源

### 技術支援
- Keysight Technologies：產品諮詢與 PROPSIM 支援
- Ettus Research (NI)：USRP 支援
- ITRI：Channel emulator 規格確認

### 參考文獻
- 3GPP TR 38.811：NTN channel models
- 3GPP TS 38.101-5：NTN UE radio transmission and reception
- Keysight S8825A：Satellite Channel Emulation Guide

### 線上資源
- GNU Radio：https://www.gnuradio.org/
- srsRAN：https://www.srslte.com/
- UHD Documentation：https://files.ettus.com/manual/

## 十、安全注意事項

### RF 暴露安全
- L-band (1-2 GHz) 功率密度限值：
  - 職業暴露：50 W/m²
  - 公眾暴露：10 W/m²
- 保持安全距離（至少 50cm from 天線）
- 使用 RF 遮蔽箱進行大功率測試

### 設備操作安全
- 確保適當接地
- 避免熱插拔 RF 連接
- 使用限幅器保護敏感設備
- 定期檢查線纜完整性

---

**文件版本**：1.0
**更新日期**：2025年11月18日
**作者**：5G NTN 實驗團隊

---

## 附錄A：ITRI Channel Emulator 可能配置

根據最新資訊分析，ITRI 最可能使用的配置：

### 選項1：Keysight PROPSIM FS16 + S8825A Toolset
- **優點**：成本效益高，足夠 30MHz 頻寬測試
- **配置建議**：
  ```
  Channel Model: 3GPP TR 38.811 NTN-TDL-D
  Delay Profile: GEO satellite (250-280ms RTT)
  Doppler: Static (GEO scenario)
  Path Loss: 190dB (typical GEO)
  ```

### 選項2：Keysight PROPSIM F64（高階選項）
- **優點**：更多通道，支援 MIMO，未來擴充性
- **適用於**：Phase array 天線測試

## 附錄B：快速故障排查指南

### 症狀：無法建立連接
1. 檢查頻率設定（TX/RX 頻率對應）
2. 確認功率等級（是否過低）
3. 驗證時脈同步
4. 檢查天線/線纜連接

### 症狀：高 EVM/BER
1. 降低發射功率（避免非線性）
2. 檢查 IQ imbalance
3. 確認取樣率設定
4. 測量 SNR

### 症狀：不穩定連接
1. 檢查 USB 供電（B210）
2. CPU 節流確認
3. Buffer overflow/underflow
4. 溫度監控

## 附錄C：Channel Emulator SCPI 命令範例

```python
# Keysight PROPSIM 基礎控制範例
import pyvisa

rm = pyvisa.ResourceManager()
emulator = rm.open_resource('TCPIP::192.168.1.100::INSTR')

# 設定 GEO satellite channel
emulator.write('CHAN:PROF:LOAD "3GPP_38811_NTN_GEO"')
emulator.write('CHAN:DELAY 250E-3')  # 250ms delay
emulator.write('CHAN:LOSS 190')       # 190dB path loss
emulator.write('CHAN:FREQ 1.8E9')     # 1.8 GHz center frequency
emulator.write('CHAN:BAND 30E6')      # 30 MHz bandwidth

# 啟動 channel emulation
emulator.write('CHAN:STATE ON')
```

---

此文件為 5G NTN 實驗的完整準備指南，請根據實際情況調整參數與配置。
