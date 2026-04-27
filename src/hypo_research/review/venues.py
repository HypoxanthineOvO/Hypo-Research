"""Venue profiles for simulated paper review."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VenueProfile:
    """Review criteria for a specific venue."""

    id: str
    name: str
    full_name: str
    category: str
    focus: list[str]
    typical_accept_rate: str | None
    review_criteria: str
    page_limit: int | None
    review_style: str | None = None


VENUES: dict[str, VenueProfile] = {
    "tcas1": VenueProfile("tcas1", "TCAS-I", "IEEE Transactions on Circuits and Systems I", "circuits", ["理论深度", "电路创新性", "数学推导严谨", "仿真与实测对比"], None, "注重理论贡献和电路设计创新。需要完整的数学分析和仿真/测量验证。", 14, "期刊审稿，多轮 revision 机会。审稿人期望看到完整的数学推导和仿真/实测对比。"),
    "tcas2": VenueProfile("tcas2", "TCAS-II", "IEEE Transactions on Circuits and Systems II: Express Briefs", "circuits", ["简洁创新", "实用性", "brief 格式"], None, "Express Brief 格式，注重简洁的技术贡献。篇幅限制严格。", 5, "Express Brief 格式，5 页限制极严。审稿人首先看篇幅是否精炼，冗余即扣分。"),
    "tvlsi": VenueProfile("tvlsi", "TVLSI", "IEEE Transactions on Very Large Scale Integration Systems", "circuits", ["VLSI 系统", "实现质量", "面积/功耗/性能权衡"], None, "关注 VLSI 系统创新和完整实现评估。", 14, "VLSI 期刊审稿强调完整系统实现和面积/功耗/性能权衡，审稿人通常要求更充分的实验和消融。"),
    "isscc": VenueProfile("isscc", "ISSCC", "IEEE International Solid-State Circuits Conference", "circuits", ["芯片实测结果", "性能指标对比", "工艺节点", "FoM"], "30%", "顶级电路会议，必须有芯片实测数据。Performance FoM 对比是核心。", None, "芯片实测是铁律。仅有仿真结果的论文几乎不可能被接收。FoM 对比表是必须项。"),
    "iscas": VenueProfile("iscas", "ISCAS", "IEEE International Symposium on Circuits and Systems", "circuits", ["技术贡献", "仿真验证", "应用场景"], "50%", "综合性电路会议，接受仿真级工作，注重技术贡献清晰度。", 5, "综合性会议，接受仿真级工作，但审稿人期望技术贡献清晰。录取率 ~50%，竞争相对温和。"),
    "aicas": VenueProfile("aicas", "AICAS", "IEEE International Conference on Artificial Intelligence Circuits and Systems", "circuits", ["AI 芯片", "硬件加速", "能效比", "算法-硬件协同"], None, "AI 电路专题会议，关注算法与硬件的协同设计和能效。", 5, "AI+电路交叉会议。审稿人特别关注算法-硬件协同设计的合理性。"),
    "cicc": VenueProfile("cicc", "CICC", "IEEE Custom Integrated Circuits Conference", "circuits", ["定制电路创新", "实测数据", "设计方法学"], "35%", "定制集成电路会议，偏重设计创新和实测验证。", 4, "偏重定制设计创新。审稿人对设计方法学有较高要求。"),
    "dac": VenueProfile("dac", "DAC", "Design Automation Conference", "eda", ["EDA 方法创新", "scalability", "实际设计流程适用性", "runtime 对比"], "23%", "EDA 顶会，方法需有实际设计流程中的价值。scalability 和 runtime 是关键。", 6, "EDA 顶会，审稿极度看重 runtime 和 scalability。'你的方法比暴力搜索快多少'是灵魂问题。不接受纯理论工作，必须有实际设计流程中的验证。"),
    "date": VenueProfile("date", "DATE", "Design, Automation and Test in Europe", "eda", ["设计自动化", "测试", "嵌入式系统", "可靠性"], "25%", "欧洲 EDA 顶会，覆盖设计、自动化和测试全流程。", 6, "欧洲 EDA 顶会。审稿风格比 DAC 略温和，但对测试和可靠性维度有独特关注。"),
    "aspdac": VenueProfile("aspdac", "ASP-DAC", "Asia and South Pacific Design Automation Conference", "eda", ["设计自动化", "物理设计", "低功耗设计"], "30%", "亚太 EDA 会议，风格与 DAC 接近但录取率略高。", 6, "亚太 EDA 会议，风格与 DAC 接近但录取率略高。对区域性研究更友好。"),
    "iccad": VenueProfile("iccad", "ICCAD", "IEEE/ACM International Conference on Computer-Aided Design", "eda", ["CAD 方法", "算法创新", "工业规模验证"], "25%", "EDA/CAD 顶会，要求方法创新与工业规模实验同时成立。", 8, "CAD 顶会，审稿人会同时追问算法 novelty、工业 benchmark 规模和与现有 flow 的兼容性。"),
    "isca": VenueProfile("isca", "ISCA", "International Symposium on Computer Architecture", "architecture", ["架构创新", "性能评估", "workload 分析", "可扩展性"], "18%", "体系结构顶会，需要新颖的架构思想和严谨的性能评估。", 11, "体系结构顶会，审稿极严。Cycle-accurate simulation 是底线，area/power/performance 三角权衡是核心评判标准。审稿人经常要求补充 workload 分析。"),
    "micro": VenueProfile("micro", "MICRO", "IEEE/ACM International Symposium on Microarchitecture", "architecture", ["微架构创新", "cycle-accurate 仿真", "面积/功耗/性能权衡"], "20%", "微架构顶会，实验需要 cycle-accurate 级别的仿真验证。", 11, "微架构顶会。审稿人对仿真方法论极其挑剔——用 gem5 还是自研 simulator？仿真配置是否合理？"),
    "hpca": VenueProfile("hpca", "HPCA", "IEEE International Symposium on High-Performance Computer Architecture", "architecture", ["高性能计算", "存储系统", "互连", "加速器"], "22%", "高性能架构会议，偏重系统级性能和可扩展性。", 11, "偏重系统级评估。审稿人关注可扩展性和真实 workload 表现。"),
    "asplos": VenueProfile("asplos", "ASPLOS", "International Conference on Architectural Support for Programming Languages and Operating Systems", "architecture", ["软硬件协同", "系统设计", "编程语言支持", "OS/编译器/架构交叉"], "25%", "软硬件协同顶会，需要跨层次的系统性贡献。", 11, "跨层次顶会（OS/编译/架构交叉）。审稿人期望论文在多个层次都有贡献，纯单层优化可能被质疑影响力不够。"),
    "neurips": VenueProfile("neurips", "NeurIPS", "Conference on Neural Information Processing Systems", "ml", ["novelty", "理论贡献", "实验充分性", "reproducibility", "broader impact"], "25%", "ML 顶会，强调 novelty 和理论深度。实验需全面且可复现。", 9, "ML 顶会但审稿质量参差不齐。理论论文容易高分通过（审稿人看不懂不敢打低分），应用论文反而被审得更严。Reproducibility Checklist 必须认真填写。投稿量近 3 万，审稿人压力极大。"),
    "icml": VenueProfile("icml", "ICML", "International Conference on Machine Learning", "ml", ["方法新颖性", "理论分析", "实验严谨性"], "27%", "ML 顶会，重视方法贡献、理论解释和严格实验。", 9, "ML 顶会，审稿文化和 NeurIPS 接近。理论、实验、可复现性都重要，应用型论文会被严格追问 baseline 和统计显著性。"),
    "iclr": VenueProfile("iclr", "ICLR", "International Conference on Learning Representations", "ml", ["representation learning", "清晰 idea", "实验洞察", "开放评审可辩护性"], "30%", "强调清晰的核心 idea、实验洞察和可复现性。", 9, "OpenReview 公开审稿。审稿人意见会被作者和社区公开质疑，因此具体证据、代码一致性和可复现性尤其重要。"),
    "aaai": VenueProfile("aaai", "AAAI", "AAAI Conference on Artificial Intelligence", "ml", ["AI 方法创新", "理论或应用贡献", "实验对比"], "20%", "综合性 AI 顶会，方法和应用并重。", 7, "综合性 AI 会议。2022 年录取率仅 15%，审稿人水平方差大。Phase 1/Phase 2 双阶段评审，两个审稿人都打低分则直接淘汰。"),
    "cvpr": VenueProfile("cvpr", "CVPR", "IEEE/CVF Conference on Computer Vision and Pattern Recognition", "vision", ["视觉方法创新", "SOTA 性能", "visual results", "ablation study"], "25%", "CV 顶会，visual results 和 ablation study 是标配。", 8, "CV 顶会，visual results 是第一评判标准。没有好看的可视化对比图几乎不可能 Accept。Ablation study 是标配。格式违规（外部链接、匿名化不彻底）会被举报。"),
    "iccv": VenueProfile("iccv", "ICCV", "IEEE/CVF International Conference on Computer Vision", "vision", ["视觉方法创新", "理论深度", "大规模实验"], "26%", "CV 顶会，偏重方法创新和理论深度。", 8, "与 CVPR 风格接近但偏重方法创新。审稿人对'为什么不用更简单的方法'这类问题特别敏感。"),
    "eccv": VenueProfile("eccv", "ECCV", "European Conference on Computer Vision", "vision", ["视觉方法", "欧洲风格偏理论", "数学推导"], "28%", "欧洲 CV 顶会，偏重理论和数学推导。", 14, "欧洲 CV 顶会，审稿风格偏理论。对数学推导和形式化描述有更高期望。"),
    "siggraph": VenueProfile("siggraph", "SIGGRAPH", "ACM SIGGRAPH", "graphics", ["视觉效果", "渲染质量", "实时性能", "用户研究"], "25%", "图形学顶会，visual quality 是第一评判标准。", None, "图形学顶会，visual quality 是硬指标。审稿人会仔细看 supplemental video。用户研究（user study）在某些方向是必须项。"),
}


def get_review_venue(venue_id: str) -> VenueProfile:
    """Return a review venue profile by id."""
    key = venue_id.lower()
    if key not in VENUES:
        choices = ", ".join(sorted(VENUES))
        raise KeyError(f"Unknown review venue '{venue_id}'. Available: {choices}")
    return VENUES[key]
