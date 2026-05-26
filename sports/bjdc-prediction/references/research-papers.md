# 北单预测前沿论文速查

> 最后更新：2026-05-24 | 来源：ArXiv + Semantic Scholar

## 一级相关（直接可落地）

### 1. 市场校准模型
- **标题**: A market-calibrated accelerated failure time model for in-play football forecasting
- **作者**: Clegg, Song, Cartlidge (2026-05-15)
- **来源**: ArXiv 2605.16066
- **核心**: 用 Betfair 赔率联合校准 1X2 和大小球市场，模型准确率 70.2% vs 市场 70.6%，回测 ROI 4.5%
- **北单映射**: 用北单让球三赔校准 λ₁, λ₂

### 2. 亚洲让球盘效率研究
- **标题**: Investigating the efficiency of the Asian handicap football betting market with ratings and Bayesian networks
- **来源**: ArXiv
- **核心**: 第一本专门为亚洲让球盘开发的预测模型，13个英超赛季数据
- **北单映射**: 贝叶斯网络 + 评级系统组合

### 3. Dixon-Coles 扩展
- **标题**: Extending the Dixon and Coles model: an application to women's football data
- **来源**: ArXiv
- **核心**: Dixon-Coles τ 是 Sarmanov 族的特例，可扩展到更多比分组合
- **北单映射**: 扩展 τ 修正到-1让球关键比分（2-1让平等）

### 4. 足球比赛相依性
- **标题**: On the dependence in football match outcomes: traditional model assumptions and an alternative proposal
- **来源**: ArXiv
- **核心**: 挑战独立泊松假设，论证两队进球存在相关性
- **北单映射**: 支持双变量泊松

## 二级相关（方法论参考）

### 5. 随机建模
- **标题**: Stochastic modelling of football matches
- **来源**: ArXiv
- **核心**: Cox过程（双随机泊松），进球强度随比赛状态变化
- **北单映射**: 让球深盘时领先方收兵效应

### 6. Glicko-2 世界杯预测
- **标题**: Nested Zero Inflated Generalized Poisson Regression for FIFA World Cup 2022
- **来源**: ArXiv 2206.09995 (相关)
- **核心**: Glicko-2评级 + 零膨胀泊松
- **北单映射**: 替代简单排名差

### 7. 机器学习投注
- **标题**: The Evolution of Football Betting - A Machine Learning Approach to Match Outcome Forecasting and Bookmaker Odds Estimation
- **来源**: ArXiv
- **核心**: 机器学习预测比赛结果并估算赔率
- **北单映射**: XGBoost分类层思路

### 8. Axial Transformer
- **标题**: Large-Scale In-Game Outcome Forecasting for Match, Team and Players in Football using an Axial Transformer Neural Network
- **来源**: ArXiv
- **核心**: 深度学习在足球预测的应用
- **北单映射**: 远期参考，需要详细球员数据

## Semantic Scholar 补充

### 9. ELO 预测
- **标题**: Football Prediction Model Based on the Teams' Elo Ratings and Scoring Indicators (2025)
- **DOI**: 10.61440/jjmm.2025.v1.02

### 10. 惩罚回归
- **标题**: Development of Score Prediction Model for English Premier League Using Penalized Regression Analysis (2022)
- **DOI**: 10.37181/jscs.2022.6.3.051

### 11. 梯度提升
- **标题**: Data-Driven Prediction of Football Player Positions Using Gradient Boosting Ensemble Models (2025)
- **DOI**: 10.1109/ASIANCON66527.2025.11280854
