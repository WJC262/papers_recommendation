"""
service.py
-----------------------------------------------------------------
把检索逻辑封装成 "纯 Python" 函数，供 FastAPI 调用
"""
# ★ 直接复用你现有的 retrieval_cpu.py
import retrieval_cpu as rc

# search(...) 返回结果、命中数量、阈值
def search(query: str, selected_journals=None):
    """
    搜索论文
    :param query: 查询词
    :param selected_journals: 选择的期刊代码列表，如 ["jtysgcyxxxb", "gljtkj"]
    """
    return rc.search(query, selected_journals)

# 获取可用期刊列表
def get_journals():
    """获取所有可用的期刊列表"""
    return rc.get_available_journals()

# get_papers_by_year_issue(...) 返回指定年份期数的论文列表
def get_papers_by_year_issue(year: str, issue: str, journal_code: str = None):
    """
    根据年份和期数获取论文列表
    :param year: 年份
    :param issue: 期数
    :param journal_code: 期刊代码，如果指定则只返回该期刊的论文
    """
    return rc.get_papers_by_year_issue(year, issue, journal_code)

