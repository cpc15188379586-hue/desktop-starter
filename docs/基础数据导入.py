#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jsbos-hdms 基础数据一键导入脚本
================================

读取《基础数据准备-导入模板-*.xlsx》，按模板第 2 行标注的导入顺序写库。

默认 dry-run（执行全部 SQL 但最后回滚，不落库）。确认无误后加 --execute。

用法
----
    python 基础数据导入.py                                  # 演练，不写库
    python 基础数据导入.py --execute                        # 真正写库
    python 基础数据导入.py --execute --only 治疗室,床位      # 只导指定表
    python 基础数据导入.py --db jsbos_hdms_v3x_rkkj --tenant rkkj
    python 基础数据导入.py --xlsx 另一个模板.xlsx

幂等性
------
所有表都先判重再插入，重复执行不会产生脏数据：
    字典分类 → 按分类编码
    字典值   → 按 (字典类型编码 + 名称)
    制造厂商 → 按厂商名称
    设备型号 → 按型号名称
    治疗室/分组/床位/班次/透析机/人员/患者 → 按名称或编号
    抗凝剂/通路/透析液/滤器 → 按名称
    患者通路/联系人 → 按 (患者ID + 通路编码/联系人)
    治疗方案 → 按 (患者ID + 计划名称)
    患者排班 → 按 (计划ID + 第几周 + 星期 + 班次 + 床位)

模板版本（2026-11-09 起）
------
在原有 17 张 sheet 基础上新增 3 张：
    字典值   base_dictionary_data    导入顺序 1/20
    制造厂商 hdms_dict_factory       导入顺序 2/20
    设备型号 hdms_dict_eq_type       导入顺序 3/20
透析机的「设备型号」「制造厂商」列填名称，脚本自动换成主键写入
（f_equip_type / f_factory_id）。

床位 ↔ 透析机（2026-11-11 起）
------------------------------
业务上是 id 关联，模板里不放雪花 ID，只填名称：
    「床位」sheet 的「透析机」列 = 床位 → 设备，脚本按名称查 hdms_eq_equipment.f_id
      写入 hdms_bed_device_info.f_docu_id（以本列为准）；
    「透析机」sheet 的「放置床位」= 同一关联的反向写法，二选一填，两边都填必须一致。

患者治疗方案 / 排班（2026-11-11 起）
----------------------------------
    患者-治疗方案 → hdms_treat_plan：患者姓名→f_patient_id，是/否→1/0，
                    计划名称建议「N周M次」并与 周期/次数 交叉校验
    患者排班表   → hdms_treat_plan_schedule：患者+计划名称→f_plan_id，周一~周日→1~7，
                    班次/床位/治疗室名称→f_id，透析器/灌流器名称→DICT_EXP_INFO 编码，
                    治疗模式名称→TREAT_MODE 编码；导入前校验 第几周 ≤ 周期、明细条数 = 次数，
                    并按「床位+班次+第几周+星期几」查重，存在冲突直接报错不落库。

退出码：0 成功；1 有失败项；2 参数或文件问题。
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
import traceback

try:
    import openpyxl
    import pymysql
except ImportError as e:  # pragma: no cover
    sys.exit('缺少依赖：pip install openpyxl pymysql  (%s)' % e)


# ============================================================================
# 一、配置区：换环境只改这一段
# ============================================================================

HERE = os.path.dirname(os.path.abspath(__file__))


def _default_xlsx() -> str:
    """取目录下版本最新的《基础数据准备-导入模板-YYYYMMDD.xlsx》，避免模板换版后还要改代码。

    文件名带日期，故字典序即版本序；排除 Excel 打开时生成的 ~$ 锁文件。
    """
    import glob
    cands = [p for p in glob.glob(os.path.join(HERE, '基础数据准备-导入模板-*.xlsx'))
             if not os.path.basename(p).startswith('~$')]
    if cands:
        return max(cands)
    return os.path.join(HERE, '基础数据准备-导入模板-20261111.xlsx')


DEFAULT_XLSX = _default_xlsx()

DB = {
    'host': '8.130.180.237',
    'port': 33306,
    'user': 'root',
    'password': 'rongke@2022',
    'database': 'jsbos_hdms_v3x_rkkjmyj2',
    'charset': 'utf8mb4',
}

TENANT = 'rkkj'          # 租户码，写入 f_tenant_id
HOSPITAL_AREA = '1'      # 院区：1=浑南院区 2=皇姑院区
SYSTEM_TYPE = '1'        # 系统类型：1=血透 2=腹透 3=CRRT 4=CKD
TREAT_AREA = '0'         # 病区：0=一楼透析室 1=二楼透析室

# 兜底默认值：只保留「库中 NOT NULL 且无默认值」的字段，其余交给库自己填
#   实测 sql_mode 含 STRICT_TRANS_TABLES，不传以下 3 列会直接报
#   1364 Field doesn't have a default value，删不掉：
#       f_diagnosis / f_fistula_position / f_fistula_location
#   库中已有默认值，无需兜底：f_source(默认1) f_identity_type(默认1)
#       f_citizenship(默认CN) f_treat_state(默认1) f_cd_flag(默认0) f_high_risk(默认0)
#   可空，无需兜底：base_user.f_dept、base_user.f_password
DEFAULT_PATIENT_DIAGNOSIS = 'N18.900'       # f_diagnosis 必填，ICD10 码=慢性肾脏病5期
DEFAULT_VAS_POSITION = 'L'                  # f_fistula_position 必填，L=左 R=右
DEFAULT_VAS_LOCATION = '1'                  # f_fistula_location 必填，1=前臂
DEFAULT_USER_PASSWORD = '123456'            # 业务必填（不填则无法登录），非 DB 约束

# 床位归组：以「床位」sheet 的「治疗区域」列为准，脚本按分组名称查 hdms_bed_group_info.f_id。
#   该列留空时才用下方 ROOM_GROUP 按治疗室兜底，并在导入报告里告警。
#   旧版按床号分段（1-8/9-17/18-22）的硬编码已废弃：跨治疗室、22 床以后会错归。
# 治疗室 → 床位分组（仅兜底用）
ROOM_GROUP = {
    '治疗大厅北面': 'A区',
    '治疗大厅南面': 'B区',
    '急诊间': '感染区',
    'VIP1间': 'VIP1区',
    'VIP2间': 'VIP2区',
}

# 治疗室配色（f_color 非空，按顺序循环取）
ROOM_COLORS = ['#e99b9b', '#fbd05b', '#a3ffb2', '#93c5f5', '#c7a3f5',
               '#f5a3c7', '#a3e0f5', '#f5cba3', '#b0b0b0', '#6760c7']

# 职务 → (JOB_TYPE 编码, 角色)
JOB_MAP = {
    '主任':   ('101', 'zzys'),   # 医生角色
    '医生':   ('102', 'zzys'),
    '护士长': ('201', 'hs'),     # 护士角色
    '护士':   ('202', 'hs'),
    '技师':   ('301', 'hs'),
}
# 角色编码 → base_role.f_id（运行时会按编码重新查，这里只是兜底）
ROLE_FALLBACK = {
    'zzys': '844190987684180613',
    'hs': '844190740253799045',
}

# 抗凝剂名称 → ANTI_TYPE 编码
# 注意「肝素钠」必须排在「低分子肝素钠」之前按精确键匹配，否则会被包含关系误判
ANTI_TYPE_MAP = {
    '无肝素': '0', '肝素钠': '1', '低分子肝素钙': '2', '低分子肝素钠': '3',
    '枸橼酸钠': '4', '阿加曲班': '5', '萘莫司他': '6', '普通肝素': '1',
}

# 通路名称 → (代码, 类别, 简称)
#   类别 1=内瘘 2=临时/长期置管 4=移植血管 5=其他通路
VAS_MAP = {
    '动静脉内瘘':   ('DJMNL', '1', 'L'),
    '颈内静脉置管': ('JNJMZG', '2', 'G'),
    '颈静脉置管':   ('JNJMZG', '2', 'G'),
    '锁骨下静脉置管': ('SGXJMZG', '2', 'G'),
    '股静脉置管':   ('GJMZG', '2', 'G'),
    '半永久静脉置管': ('BYJJMZG', '2', 'G'),
    '自体血管移植': ('ZTMGZY', '4', 'C'),
    '移植人造血管': ('YZRZXG', '4', 'C'),
    '直接血管穿刺': ('ZJXGCC', '5', 'C'),
    '人工血管穿刺': ('RGXGCC', '5', 'C'),
}

# 耗材类别：透析器 01 / 灌流器 02
EXP_ATTR_MAP = {'透析器': '01', '灌流器': '02', '滤器': '01'}
# 设备类别：透析机 01 / 血滤机 02
EQUIP_KIND_MAP = {'透析机': '01', '血滤机': '02', 'CRRT机': '03'}

# 患者表「通路位置」列里的简称 → 血管通路类型标准名
# （原表填的是通路类型，不是左/右位置；位置由 DEFAULT_VAS_POSITION 统一给）
PATIENT_VAS_ALIAS = {
    '内瘘': '动静脉内瘘',
    '自体瘘': '动静脉内瘘',
    '颈静脉置管': '颈内静脉置管',
    '颈内静脉置管': '颈内静脉置管',
    '锁骨下静脉置管': '锁骨下静脉置管',
    '股静脉置管': '股静脉置管',
    '半永久静脉置管': '半永久静脉置管',
    '长期置管': '半永久静脉置管',
    '临时置管': '中心静脉置管',
    '中心静脉置管': '中心静脉置管',
    '人造血管': '移植人造血管',
    '自体血管移植': '自体血管移植',
    '直接穿刺': '直接血管穿刺',
    '人工血管穿刺': '人工血管穿刺',
}

ID_TYPE_ID_CARD = '1'    # 身份证

# 导入顺序（与模板第 2 行一致，共 20 项）
IMPORT_ORDER = [
    '字典分类', '字典值', '制造厂商', '设备型号',
    '治疗模式', '保险类型', '抗凝剂种类', '血管通路类型',
    '透析液', '透析滤器', '班次', '治疗室', '治疗区域', '床位',
    '透析机', '人员', '患者-基本信息', '套餐', '患者-治疗方案', '患者排班表',
]

# 「字典值」sheet 允许导入的字典类型白名单（防止往里塞不该由模板维护的分类）
DICT_VALUE_TYPES = {
    'EQUIP_KIND', 'EQ_STATE', 'JOB_TYPE', 'DEPT_ID', 'VAS_TYPE',
    'EXP_ATTR', 'EXP_UNITS', 'ANTI_TYPE', 'sex', 'Nation',
    'BLOOD_TYPE', 'MARITAL_STATUS', 'SOURCE', 'RELATION', 'TREAT_STATE',
    'IDENTITY_TYPE',
}


# ============================================================================
# 二、基础工具
# ============================================================================

class Snowflake:
    """与库里 19 位雪花 ID 兼容的主键生成器。"""

    EPOCH = 1577836800000  # 2020-01-01 00:00:00

    def __init__(self, worker: int = 1):
        self.worker = worker & 0x3FF
        self.seq = 0
        self.last = -1

    def next(self) -> str:
        ts = int(time.time() * 1000)
        if ts == self.last:
            self.seq = (self.seq + 1) & 0xFFF
            if self.seq == 0:
                while ts <= self.last:
                    ts = int(time.time() * 1000)
        else:
            self.seq = 0
        self.last = ts
        return str(((ts - self.EPOCH) << 22) | (self.worker << 12) | self.seq)


SNOW = Snowflake()


def md5hex(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def enc_password(plain: str, secretkey: str) -> str:
    """与核心包登录校验一致的两步加盐 MD5。"""
    return md5hex(md5hex(plain) + secretkey.lower())


def cell_str(v) -> str:
    """单元格转字符串，规避 Excel 把长数字变科学计数法/加 .0。"""
    if v is None:
        return ''
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, bool):
        return '1' if v else '0'
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else str(v)
    if isinstance(v, int):
        return str(v)
    if isinstance(v, dt.datetime):
        return v.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(v, dt.date):
        return v.strftime('%Y-%m-%d')
    if isinstance(v, dt.time):
        return v.strftime('%H:%M:%S')
    return str(v).strip()


def to_time(v) -> str:
    """'07:30' / time / '7:30:00' → 'HH:MM:SS'"""
    s = cell_str(v)
    if not s:
        return ''
    if isinstance(v, dt.time):
        return v.strftime('%H:%M:%S')
    m = re.match(r'^(\d{1,2}):(\d{2})(?::(\d{2}))?$', s)
    if not m:
        raise ValueError('时间格式不对：%r' % v)
    return '%02d:%s:%s' % (int(m.group(1)), m.group(2), m.group(3) or '00')


def to_date(v) -> str:
    """日期单元格 → 'YYYY-MM-DD'；空返回 ''。"""
    if v is None or (isinstance(v, str) and not v.strip()):
        return ''
    if isinstance(v, dt.datetime):
        return v.strftime('%Y-%m-%d')
    if isinstance(v, dt.date):
        return v.strftime('%Y-%m-%d')
    m = re.match(r'^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', cell_str(v))
    if not m:
        raise ValueError('日期格式不对：%r（要 yyyy-MM-dd）' % v)
    return '%04d-%02d-%02d' % (int(m.group(1)), int(m.group(2)), int(m.group(3)))


WEEK_NAME_BY_DAY = {1: '周一', 2: '周二', 3: '周三', 4: '周四',
                   5: '周五', 6: '周六', 7: '周日'}
WEEK_DAYS = {'周一': 1, '周二': 2, '周三': 3, '周四': 4, '周五': 5, '周六': 6, '周日': 7,
             '星期一': 1, '星期二': 2, '星期三': 3, '星期四': 4, '星期五': 5, '星期六': 6,
             '星期天': 7, '周天': 7}


def to_week_day(v) -> int:
    """周一~周日 / 1~7 → int(1~7)，认不出返回 0。"""
    s1 = cell_str(v).replace(' ', '')
    if not s1:
        return 0
    if s1.isdigit():
        n = int(s1)
        return n if 1 <= n <= 7 else 0
    return WEEK_DAYS.get(s1, 0)


def yes_no_char(v, default='1') -> str:
    """是/否、1/0、Y/N → '1'/'0'（f_auto_generate 这类 char(1) 字段）。"""
    t = cell_str(v).lower()
    if t in ('是', '1', 'y', 'yes', 'true'):
        return '1'
    if t in ('否', '0', 'n', 'no', 'false'):
        return '0'
    return default


def gen_mode_char(v, default='1') -> str:
    """按周期滚动→1 / 按时间段生成→0；也认 1、0。"""
    t = cell_str(v)
    if not t:
        return default
    if '周期' in t or t == '1':
        return '1'
    if '时段' in t or t == '0':
        return '0'
    return default


def fmt_td(v) -> str:
    """MySQL TIME 取回是 timedelta，统一成 HH:MM:SS 便于比较。"""
    if isinstance(v, dt.timedelta):
        s = int(v.total_seconds())
        return '%02d:%02d:%02d' % (s // 3600, s % 3600 // 60, s % 60)
    return cell_str(v)


def norm_name(s: str) -> str:
    """名称归一化：去空白、全角括号转半角，用于宽松判重。"""
    s = re.sub(r'\s+', '', s or '')
    return s.replace('（', '(').replace('）', ')')


def name_matches(a: str, b: str) -> bool:
    """名称判重：完全相同，或一方是另一方的前缀（容忍模板里的截断）。"""
    x, y = norm_name(a), norm_name(b)
    if not x or not y:
        return False
    if x == y:
        return True
    short, long_ = (x, y) if len(x) <= len(y) else (y, x)
    return len(short) >= 3 and long_.startswith(short) and len(long_) - len(short) <= 2


def parse_id_card(idno: str):
    """身份证 → (生日, 性别)。校验位不对也返回，只是标记。"""
    idno = (idno or '').strip().upper()
    if len(idno) != 18:
        return None, None
    try:
        birthday = dt.date(int(idno[6:10]), int(idno[10:12]), int(idno[12:14]))
    except ValueError:
        return None, None
    sex = '1' if int(idno[16]) % 2 == 1 else '2'
    return birthday, sex


def calc_age(birthday: dt.date) -> int:
    today = dt.date.today()
    return today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))


# ============================================================================
# 三、Excel 读取
# ============================================================================

class Sheet:
    """一张数据 sheet：第 1 行说明，第 2 行表名，第 3 行字段名，第 4 行起数据。"""

    def __init__(self, ws):
        self.title = ws.title
        self.name_row2 = cell_str(ws.cell(row=2, column=1).value)
        self.headers = [cell_str(ws.cell(row=3, column=c).value) for c in range(1, ws.max_column + 1)]
        self.rows = []
        for r in range(4, ws.max_row + 1):
            values = [ws.cell(row=r, column=c).value for c in range(1, ws.max_column + 1)]
            if all(v is None or cell_str(v) == '' for v in values):
                continue
            rec = {'__row__': r}
            for h, v in zip(self.headers, values):
                if h:
                    rec[h] = v
            self.rows.append(rec)

    def table_name(self) -> str:
        """从第 2 行抓 实际表名：xxx"""
        m = re.search(r'实际表名[:：]\s*([A-Za-z0-9_]+)', self.name_row2)
        return m.group(1) if m else ''

    def get(self, row: dict, header: str, default='') -> str:
        return cell_str(row.get(header))


def load_book(path: str) -> dict:
    if not os.path.exists(path):
        sys.exit('模板不存在：%s' % path)
    wb = openpyxl.load_workbook(path, data_only=True)
    return {ws.title: Sheet(ws) for ws in wb.worksheets}


# ============================================================================
# 四、数据库访问
# ============================================================================

class DB2:
    def __init__(self, cfg, dry_run: bool):
        self.cfg = dict(cfg)
        self.dry = dry_run
        self.conn = pymysql.connect(**self.cfg, autocommit=False)
        self.cur = self.conn.cursor()
        # 会话排序规则对齐表列，避免 1267 Illegal mix of collations
        try:
            self.cur.execute("SET collation_connection = 'utf8mb4_general_ci'")
        except Exception:
            pass
        self.schema = self.cfg['database']

    # ---------- 查询 ----------
    def one(self, sql, params=None):
        self.cur.execute(sql, params or ())
        return self.cur.fetchone()

    def all(self, sql, params=None):
        self.cur.execute(sql, params or ())
        return self.cur.fetchall()

    def scalar(self, sql, params=None, default=None):
        row = self.one(sql, params)
        return row[0] if row else default

    # ---------- 写入 ----------
    def insert(self, table: str, data: dict) -> None:
        cols = ', '.join('`%s`' % c for c in data)
        marks = ', '.join(['%s'] * len(data))
        sql = 'INSERT INTO `%s` (%s) VALUES (%s)' % (table, cols, marks)
        self.cur.execute(sql, list(data.values()))

    def exists_column(self, table: str, column: str) -> bool:
        return bool(self.scalar(
            "SELECT 1 FROM information_schema.columns WHERE table_schema=%s "
            "AND table_name=%s AND column_name=%s", (self.schema, table, column)))

    def finish(self, ok: bool):
        if self.dry or not ok:
            self.conn.rollback()
        else:
            self.conn.commit()


# ============================================================================
# 五、导入结果记录
# ============================================================================

class Reporter:
    def __init__(self):
        self.items = []   # (顺序, 表, 新增, 跳过, 警告, 错误)

    def add(self, name, added=0, skipped=0, warns=None, errors=None):
        self.items.append({
            'name': name, 'added': added, 'skipped': skipped,
            'warns': warns or [], 'errors': errors or [],
        })

    def summary(self):
        ta = sum(i['added'] for i in self.items)
        ts = sum(i['skipped'] for i in self.items)
        tw = sum(len(i['warns']) for i in self.items)
        te = sum(len(i['errors']) for i in self.items)
        return ta, ts, tw, te

    def render(self):
        out = []
        out.append('')
        out.append('=' * 78)
        out.append('%-24s %8s %8s %8s %8s' % ('数据表', '新增', '跳过(已存在)', '警告', '错误'))
        out.append('-' * 78)
        for i in self.items:
            out.append('%-24s %8d %8d %8d %8d' % (
                i['name'], i['added'], i['skipped'], len(i['warns']), len(i['errors'])))
        out.append('-' * 78)
        ta, ts, tw, te = self.summary()
        out.append('%-24s %8d %8d %8d %8d' % ('合计', ta, ts, tw, te))
        out.append('=' * 78)
        for i in self.items:
            for w in i['warns'][:8]:
                out.append('  [警告] %s：%s' % (i['name'], w))
            if len(i['warns']) > 8:
                out.append('  [警告] %s：另有 %d 条同类警告（略）'
                           % (i['name'], len(i['warns']) - 8))
            for e in i['errors']:
                out.append('  [错误] %s：%s' % (i['name'], e))
        return '\n'.join(out)


# ============================================================================
# 六、字典辅助
# ============================================================================

class Dicts:
    """把库里的字典缓存到内存，按类型编码取 (编码→名称、名称→编码)。"""

    def __init__(self, db: DB2):
        self.db = db
        self.types = {}
        self.data = {}
        self._load()

    def _load(self):
        for tid, code, name in self.db.all(
                "SELECT f_id, f_en_code, f_full_name FROM base_dictionary_type "
                "WHERE IFNULL(f_delete_mark,0)=0"):
            self.types[(code or '').lower()] = {'id': tid, 'code': code, 'name': name}
        for tid, code, name, text in self.db.all(
                "SELECT f_dictionary_type_id, f_en_code, f_full_name, "
                "IFNULL(f_simple_spelling,'') FROM base_dictionary_data "
                "WHERE IFNULL(f_delete_mark,0)=0"):
            self.data.setdefault(tid, []).append({'code': code, 'name': name, 'py': text})

    def type_of(self, type_code: str):
        return self.types.get((type_code or '').lower())

    def items(self, type_code: str):
        t = self.type_of(type_code)
        return self.data.get(t['id'], []) if t else []

    def code_by_name(self, type_code: str, name: str, fuzzy=False) -> str:
        """名称 → 编码。fuzzy=True 时允许包含/前缀匹配（如 '汉' → '汉族'）。"""
        n = norm_name(name)
        if not n:
            return ''
        items = self.items(type_code)
        for it in items:
            if norm_name(it['name']) == n:
                return it['code']
        if fuzzy:
            for it in items:
                cn = norm_name(it['name'])
                if n in cn or cn in n:
                    return it['code']
        return ''

    def name_by_code(self, type_code: str, code: str) -> str:
        for it in self.items(type_code):
            if it['code'] == code:
                return it['name']
        return ''


# ============================================================================
# 七、各表导入器
# ============================================================================

class Importer:
    def __init__(self, db: DB2, book: dict, rep: Reporter):
        self.db = db
        self.book = book
        self.rep = rep
        self.dicts = Dicts(db)
        self.room_ids = {}     # 治疗室名称 → f_id
        self.group_ids = {}    # 分组名称 → f_id
        self.role_ids = {}     # 角色编码 → f_id
        self.vas_codes = {}    # 通路名称 → 编码
        self.bed_ids = {}      # 床位名称 → f_id
        self.sched_codes = {}  # 班次名称 → 编码
        self.patient_ids = {}  # 姓名 → 患者ID
        self.factory_ids = {}  # 厂商名称 → hdms_dict_factory.f_id
        self.eq_type_ids = {}  # 型号名称 → hdms_dict_eq_type.f_id
        self.eq_type_kind = {}  # 型号名称 → 设备类别编码（用于交叉校验）
        self.plan_meta = {}     # (患者姓名, 计划名称) → (计划ID, 周期, 次数)
        self.bed_room = {}      # 床位名称 → 治疗室名称（排班填治疗室留空时兜底）

    def sheet(self, name) -> Sheet | None:
        return self.book.get(name)

    # ---------------- 0. 字典分类 ----------------
    def imp_dict_type(self):
        sh = self.sheet('字典分类')
        res = self.rep
        if not sh:
            res.add('字典分类', errors=['sheet 缺失'])
            return
        added = skipped = 0
        warns, errors = [], []
        for row in sh.rows:
            code = sh.get(row, '字典分类编码')
            name = sh.get(row, '字典分类名称')
            if not code:
                continue
            exist = self.db.one(
                "SELECT f_id FROM base_dictionary_type WHERE f_en_code=%s "
                "AND IFNULL(f_delete_mark,0)=0", (code,))
            if exist:
                skipped += 1
                continue
            tid = SNOW.next()
            self.db.insert('base_dictionary_type', {
                'f_id': tid,
                'f_parent_id': self._root_type_id(),
                'f_full_name': name,
                'f_en_code': code,
                'f_is_tree': 0,
                'f_type': 1,
                'f_enabled_mark': 1,
                'f_sort_code': int(re.sub(r'\D', '', sh.get(row, '排列顺序')) or 0),
                'f_delete_mark': None,
                'f_tenant_id': TENANT,
            })
            self.dicts.types[code.lower()] = {'id': tid, 'code': code, 'name': name}
            added += 1
        res.add('字典分类', added, skipped, warns, errors)

    def _root_type_id(self) -> str:
        rid = self.db.scalar(
            "SELECT f_id FROM base_dictionary_type WHERE f_en_code=%s LIMIT 1", ('hdms',))
        if rid:
            return rid
        rid = self.db.scalar(
            "SELECT f_id FROM base_dictionary_type WHERE f_parent_id=%s "
            "AND IFNULL(f_delete_mark,0)=0 LIMIT 1", ('-1',))
        return rid or '844225934633498309'

    # ---------------- 1. 字典值（通用字典明细） ----------------
    def imp_dict_value(self):
        sh = self.sheet('字典值')
        if not sh:
            self.rep.add('字典值', errors=['sheet 缺失'])
            return
        added = skipped = 0
        warns, errors = [], []
        for row in sh.rows:
            type_code = sh.get(row, '字典类型编码')
            name = sh.get(row, '字典值名称')
            code = sh.get(row, '字典值编码')
            if not type_code or not name:
                continue
            if type_code not in DICT_VALUE_TYPES:
                warns.append('%s 的字典类型「%s」不在白名单内，已跳过' % (name, type_code))
                continue
            t = self.dicts.type_of(type_code)
            if not t:
                errors.append('字典分类「%s」不存在，请先导入「字典分类」' % type_code)
                continue
            items = self.dicts.items(type_code)
            if any(norm_name(x['name']) == norm_name(name) for x in items):
                skipped += 1
                continue
            if not code:
                errors.append('%s 缺「字典值编码」（f_en_code 必填）' % name)
                continue
            if any(x['code'] == code for x in items):
                warns.append('%s 的编码 %s 在该类型下已被占用，仍按名称写入' % (name, code))
            py = sh.get(row, '拼音码')
            self.db.insert('base_dictionary_data', {
                'f_id': SNOW.next(),
                'f_parent_id': '0',
                'f_full_name': name,
                'f_en_code': code,
                'f_simple_spelling': py,
                'f_is_default': '0',
                'f_enabled_mark': 1,
                'f_dictionary_type_id': t['id'],
                'f_dictionary_type_code': type_code,
                'f_is_edit': '0',
                'f_sort_code': int(re.sub(r'\D', '', sh.get(row, '排列顺序')) or 0),
                'f_delete_mark': None,
                'f_tenant_id': TENANT,
            })
            self.dicts.data.setdefault(t['id'], []).append(
                {'code': code, 'name': name, 'py': py})
            added += 1
        self.rep.add('字典值', added, skipped, warns, errors)

    # ---------------- 2. 制造厂商 ----------------
    def imp_factory(self):
        sh = self.sheet('制造厂商')
        if not sh:
            self.rep.add('制造厂商', errors=['sheet 缺失'])
            return
        added = skipped = 0
        warns, errors = [], []
        for fid, name in self.db.all(
                "SELECT f_id, f_factory_name FROM hdms_dict_factory"):
            self.factory_ids[name] = fid
        used_codes = {r[0] for r in self.db.all(
            "SELECT f_factory_code FROM hdms_dict_factory")}
        for row in sh.rows:
            name = sh.get(row, '厂商名称')
            if not name:
                continue
            if name in self.factory_ids:
                skipped += 1
                continue
            code = sh.get(row, '厂商编码')
            if not code:
                n = 1
                while '%03d' % n in used_codes:
                    n += 1
                code = '%03d' % n
                warns.append('%s 缺厂商编码，自动生成 %s' % (name, code))
            if code in used_codes:
                errors.append('%s 的厂商编码 %s 已被占用' % (name, code))
                continue
            fid = SNOW.next()
            self.db.insert('hdms_dict_factory', {
                'f_id': fid,
                'f_factory_code': code,
                'f_factory_type': sh.get(row, '厂商类型') or '1',
                'f_factory_name': name,
                'f_country': sh.get(row, '国家') or None,
                'f_name_pycode': '',
                'f_sort_code': int(re.sub(r'\D', '', sh.get(row, '排列顺序')) or 0),
                'f_creator_time': dt.datetime.now(),
                'f_tenant_id': TENANT,
            })
            self.factory_ids[name] = fid
            used_codes.add(code)
            added += 1
        self.rep.add('制造厂商', added, skipped, warns, errors)

    # ---------------- 3. 设备型号 ----------------
    def imp_eq_type(self):
        sh = self.sheet('设备型号')
        if not sh:
            self.rep.add('设备型号', errors=['sheet 缺失'])
            return
        added = skipped = 0
        warns, errors = [], []
        if not self.factory_ids:
            for fid, name in self.db.all(
                    "SELECT f_id, f_factory_name FROM hdms_dict_factory"):
                self.factory_ids[name] = fid
        for fid, name in self.db.all(
                "SELECT f_id, f_equip_name FROM hdms_dict_eq_type"):
            self.eq_type_ids[name] = fid
        used_codes = {r[0] for r in self.db.all(
            "SELECT f_equip_type FROM hdms_dict_eq_type")}
        for row in sh.rows:
            name = sh.get(row, '型号名称')
            code = sh.get(row, '型号编码')
            if not name:
                continue
            if name in self.eq_type_ids:
                skipped += 1
                continue
            if not code:
                errors.append('%s 缺「型号编码」（f_equip_type 必填）' % name)
                continue
            if code in used_codes:
                warns.append('%s 的型号编码 %s 已被其它型号占用（编码不唯一不影响使用）' % (name, code))
            kind_name = sh.get(row, '设备类别')
            kind = self.dicts.code_by_name('EQUIP_KIND', kind_name) if kind_name else ''
            if not kind:
                kind = EQUIP_KIND_MAP.get(kind_name, '01')
                if kind_name and kind_name not in EQUIP_KIND_MAP:
                    warns.append('%s 的设备类别「%s」没匹配到，暂用 01=透析机' % (name, kind_name))
            fac_name = sh.get(row, '制造厂商')
            fac_id = self.factory_ids.get(fac_name)
            if fac_name and not fac_id:
                warns.append('%s 的厂商「%s」在制造厂商表中不存在，厂商留空' % (name, fac_name))
            fid = SNOW.next()
            self.db.insert('hdms_dict_eq_type', {
                'f_id': fid,
                'f_factory_id': fac_id,
                'f_equip_type': code,
                'f_equip_kind': kind,
                'f_equip_name': name,
                'f_creator_time': dt.datetime.now(),
                'f_sort_code': int(re.sub(r'\D', '', sh.get(row, '排列顺序')) or 0),
                'f_tenant_id': TENANT,
            })
            self.eq_type_ids[name] = fid
            used_codes.add(code)
            added += 1
        self.rep.add('设备型号', added, skipped, warns, errors)

    # ---------------- 4/5. 字典明细：治疗模式、保险类型 ----------------
    def _imp_dict_data(self, sheet_name, type_code, name_col, code_col):
        sh = self.sheet(sheet_name)
        if not sh:
            self.rep.add(sheet_name, errors=['sheet 缺失'])
            return
        added = skipped = 0
        warns, errors = [], []
        t = self.dicts.type_of(type_code)
        if not t:
            self.rep.add(sheet_name, errors=['base_dictionary_type 缺分类 %s，请先执行「字典分类」' % type_code])
            return
        for row in sh.rows:
            name = sh.get(row, name_col)
            if not name:
                continue
            code = sh.get(row, code_col)
            # 名称已存在 → 跳过；编码已存在但名称不同 → 冲突警告
            old = [x for x in self.dicts.items(type_code) if norm_name(x['name']) == norm_name(name)]
            if old:
                skipped += 1
                if code and old[0]['code'] != code:
                    warns.append('%s 已存在，库中编码 %s 与表中 %s 不一致（未改）'
                                 % (name, old[0]['code'], code))
                continue
            if code and any(x['code'] == code for x in self.dicts.items(type_code)):
                errors.append('%s 的编码 %s 已被其他项占用' % (name, code))
                continue
            if not code:
                errors.append('%s 缺「编号」，字典明细必填' % name)
                continue
            sort = int(re.sub(r'\D', '', sh.get(row, '排列顺序')) or 0)
            # 简称/拼音码：字典值表列名是「拼音码」，治疗模式表列名是「简称」，都落 f_simple_spelling。
            # 注意 f_description 在系统里存的是治疗模式配色（#RRGGBB），不能拿来存简称。
            py = sh.get(row, '简称') or sh.get(row, '拼音码') or ''
            self.db.insert('base_dictionary_data', {
                'f_id': SNOW.next(),
                'f_parent_id': '0',
                'f_full_name': name,
                'f_en_code': code,
                'f_simple_spelling': py,
                'f_is_default': '0',
                'f_enabled_mark': 1,
                'f_dictionary_type_id': t['id'],
                'f_dictionary_type_code': type_code,
                'f_is_edit': '0',
                'f_sort_code': sort,
                'f_delete_mark': None,
                'f_tenant_id': TENANT,
            })
            self.dicts.data.setdefault(t['id'], []).append({'code': code, 'name': name, 'py': py})
            added += 1
        self.rep.add(sheet_name, added, skipped, warns, errors)

    def imp_treat_mode(self):
        self._imp_dict_data('治疗模式', 'TREAT_MODE', '治疗模式名称', '编号')

    def imp_payment_mode(self):
        self._imp_dict_data('保险类型', 'PAYMENT_MODE', '医保类型', '编号')

    # ---------------- 3. 抗凝剂 ----------------
    def imp_anticoagulant(self):
        sh = self.sheet('抗凝剂种类')
        if not sh:
            self.rep.add('抗凝剂种类', errors=['sheet 缺失'])
            return
        added = skipped = 0
        warns, errors = [], []
        existing = [r[0] for r in self.db.all(
            "SELECT f_name FROM hdms_dict_anticoagulant WHERE f_tenant_id=%s "
            "AND IFNULL(f_delete_mark,0)=0", (TENANT,))]
        for row in sh.rows:
            name = sh.get(row, '抗凝剂名称')
            if not name:
                continue
            if any(name_matches(name, e) for e in existing):
                skipped += 1
                continue
            anti = sh.get(row, '抗凝剂类型')
            anti_code = self.dicts.code_by_name('ANTI_TYPE', anti) if anti else ''
            if not anti_code:
                anti_code = ANTI_TYPE_MAP.get(name, '')
            if not anti_code:
                # 按名称关键词推断
                for key, val in ANTI_TYPE_MAP.items():
                    if key in name or name in key:
                        anti_code = val
                        break
            if not anti_code:
                anti_code = '7'   # 其它抗凝剂
                warns.append('%s 没匹配到抗凝剂类型，暂用 7=其它抗凝剂' % name)
            self.db.insert('hdms_dict_anticoagulant', {
                'f_id': SNOW.next(),
                'f_name': name,
                'f_shortname': sh.get(row, '简称') or '',
                'f_anti_type': anti_code,
                'f_is_default': '0',
                'f_beforeorafter': '0',
                'f_sort_code': int(re.sub(r'\D', '', sh.get(row, '排列顺序')) or 0),
                'f_delete_mark': None,
                'f_tenant_id': TENANT,
            })
            existing.append(name)
            added += 1
        self.rep.add('抗凝剂种类', added, skipped, warns, errors)

    # ---------------- 4. 血管通路类型 ----------------
    def imp_vas(self):
        sh = self.sheet('血管通路类型')
        if not sh:
            self.rep.add('血管通路类型', errors=['sheet 缺失'])
            return
        added = skipped = 0
        warns, errors = [], []
        rows0 = self.db.all(
            "SELECT f_vas_code, f_vas_name FROM hdms_dict_vas_access WHERE f_tenant_id=%s "
            "AND IFNULL(f_delete_mark,0)=0", (TENANT,))
        existing = [(r[0], r[1]) for r in rows0]
        for row in sh.rows:
            name = sh.get(row, '血管通路类型')
            if not name:
                continue
            hit = [code for code, nm in existing if name_matches(name, nm)]
            if hit:
                self.vas_codes[name] = hit[0]
                # 也登记库中真名，供患者表按名称引用
                for code, nm in existing:
                    if name_matches(name, nm):
                        self.vas_codes[nm] = code
                skipped += 1
                continue
            code = sh.get(row, '通路代码')
            meta = VAS_MAP.get(name)
            if meta is None:
                for key, val in VAS_MAP.items():
                    if name_matches(name, key):
                        meta = val
                        break
            if not code and meta:
                code = meta[0]
            if not code:
                code = 'VAS%02d' % (len(existing) + added + 1)
            vas_type = sh.get(row, '通路类别')
            vas_type = self.dicts.code_by_name('VAS_TYPE', vas_type) if vas_type else ''
            if not vas_type and meta:
                vas_type = meta[1]
            if not vas_type:
                vas_type = '5'
                warns.append('%s 没匹配到通路类别，暂用 5=其他通路' % name)
            short = sh.get(row, '简称')
            if not short:
                short = meta[2] if meta else ('L' if '内瘘' in name else 'G')
            self.db.insert('hdms_dict_vas_access', {
                'f_id': SNOW.next(),
                'f_vas_code': code,
                'f_vas_name': name,
                'f_name_abbr': code,
                'f_shortname': short,
                'f_vas_type': vas_type,
                'f_is_default': '0',
                'f_sort_code': int(re.sub(r'\D', '', sh.get(row, '排列顺序')) or 0),
                'f_delete_mark': None,
                'f_creator_time': dt.datetime.now(),
                'f_tenant_id': TENANT,
            })
            self.vas_codes[name] = code
            existing.append((code, name))
            added += 1
        self.rep.add('血管通路类型', added, skipped, warns, errors)

    # ---------------- 5. 透析液 ----------------
    def imp_dialyzate(self):
        sh = self.sheet('透析液')
        if not sh:
            self.rep.add('透析液', errors=['sheet 缺失'])
            return
        added = skipped = 0
        warns, errors = [], []
        existing = [r[0] for r in self.db.all(
            "SELECT f_dialyzate_name FROM hdms_dict_dialyzate WHERE f_tenant_id=%s", (TENANT,))]
        seq = 0
        for row in sh.rows:
            name = sh.get(row, '名称')
            if not name:
                continue
            if any(name_matches(name, e) for e in existing):
                skipped += 1
                continue
            seq += 1
            code = sh.get(row, '透析液代码') or 'DYL%02d' % seq
            data = {
                'f_id': SNOW.next(),
                'f_dialyzate_code': code,
                'f_dialyzate_name': name,
                'f_name_pycode': '',
                'f_sort_code': int(re.sub(r'\D', '', sh.get(row, '排列顺序')) or seq),
                'f_dialyzate_conc_code': 'CT',
                'f_creator_time': dt.datetime.now(),
                'f_tenant_id': TENANT,
            }
            for col, field in (('钙浓度', 'f_ca'), ('钾浓度', 'f_k'),
                               ('钠浓度', 'f_na'), ('镁浓度', 'f_mg'),
                               ('碳酸氢根', 'f_hco3')):
                val = sh.get(row, col)
                data[field] = float(val) if val not in ('', None) else 0.0
            self.db.insert('hdms_dict_dialyzate', data)
            existing.append(name)
            added += 1
        self.rep.add('透析液', added, skipped, warns, errors)

    # ---------------- 6. 透析滤器 ----------------
    def imp_exp_info(self):
        sh = self.sheet('透析滤器')
        if not sh:
            self.rep.add('透析滤器', errors=['sheet 缺失'])
            return
        added = skipped = 0
        warns, errors = [], []
        existing = [r[0] for r in self.db.all(
            "SELECT f_exp_name FROM hdms_dict_exp_info WHERE f_tenant_id=%s "
            "AND IFNULL(f_delete_mark,0)=0", (TENANT,))]
        seq = 0
        for row in sh.rows:
            name = sh.get(row, '透析滤器')
            if not name:
                continue
            if any(name_matches(name, e) for e in existing):
                skipped += 1
                continue
            seq += 1
            attr_name = sh.get(row, '类型')
            attr = self.dicts.code_by_name('EXP_ATTR', attr_name) if attr_name else ''
            if not attr:
                attr = EXP_ATTR_MAP.get(attr_name, '01')
                if attr_name and attr_name not in EXP_ATTR_MAP:
                    warns.append('%s 的类型「%s」没匹配到耗材类别，暂用 01=透析器' % (name, attr_name))
            self.db.insert('hdms_dict_exp_info', {
                'f_id': SNOW.next(),
                'f_exp_code': sh.get(row, '滤器编码') or 'LQ%03d' % seq,
                'f_exp_name': name,
                'f_exp_short_name': name,
                'f_exp_attr': attr,
                'f_exp_specs': sh.get(row, '规格'),
                'f_exp_units': self.dicts.code_by_name('EXP_UNITS', sh.get(row, '单位')) or '1',
                'f_system_type': SYSTEM_TYPE,
                'f_enabled_mark': 1,
                'f_sort_code': int(re.sub(r'\D', '', sh.get(row, '排列顺序')) or seq),
                'f_delete_mark': None,
                'f_creator_time': dt.datetime.now(),
                'f_tenant_id': TENANT,
            })
            existing.append(name)
            added += 1
        self.rep.add('透析滤器', added, skipped, warns, errors)

    # ---------------- 7. 班次 ----------------
    def imp_schedule(self):
        sh = self.sheet('班次')
        if not sh:
            self.rep.add('班次', errors=['sheet 缺失'])
            return
        added = skipped = 0
        warns, errors = [], []
        existing_rows = self.db.all(
            "SELECT f_schedule_code, f_schedule_name, f_start_time, f_stop_time "
            "FROM hdms_dict_schedule WHERE f_tenant_id=%s AND IFNULL(f_delete_mark,0)=0",
            (TENANT,))
        existing = {(r[0] or '').lower(): r[0] for r in existing_rows}
        by_name = {r[1]: r for r in existing_rows}
        for row in sh.rows:
            name = sh.get(row, '班次名称')
            code = sh.get(row, '班次代码')
            if not name:
                continue
            if code and code.lower() in existing:
                self.sched_codes[name] = existing[code.lower()]
                skipped += 1
                continue
            hit = next((r for n, r in by_name.items() if name_matches(name, n)), None)
            if hit:
                skipped += 1
                try:
                    st, sp = to_time(row.get('开始时间')), to_time(row.get('结束时间'))
                except ValueError:
                    st = sp = ''
                if hit[0] != code:
                    warns.append('库中已有同名班次「%s」(代码 %s)，模板代码为 %s，已跳过；'
                                 '要新建请先改模板班次名' % (name, hit[0], code))
                elif st and (fmt_td(hit[2]) != st or fmt_td(hit[3]) != sp):
                    warns.append('库中班次「%s」时间为 %s-%s，模板为 %s-%s，已跳过未改'
                                 % (name, fmt_td(hit[2]), fmt_td(hit[3]), st, sp))
                continue
            try:
                start, stop = to_time(row.get('开始时间')), to_time(row.get('结束时间'))
            except ValueError as e:
                errors.append('%s：%s' % (name, e))
                continue
            if not start or not stop:
                errors.append('%s 缺开始/结束时间（都是非空字段）' % name)
                continue
            fid = SNOW.next()
            self.db.insert('hdms_dict_schedule', {
                'f_id': fid,
                'f_schedule_code': code,
                'f_schedule_name': name,
                'f_schedule_spec': sh.get(row, '班次简称') or name[:1],
                'f_start_time': start,
                'f_stop_time': stop,
                'f_hosptial_area': HOSPITAL_AREA,
                'f_chedule_remark': sh.get(row, '备注'),
                'f_sort_code': int(re.sub(r'\D', '', sh.get(row, '排列顺序')) or 0),
                'f_delete_mark': None,
                'f_tenant_id': TENANT,
            })
            self.sched_codes[name] = code
            by_name[name] = (code, name, start, stop)
            added += 1
        self.rep.add('班次', added, skipped, warns, errors)

    # ---------------- 8. 治疗室 ----------------
    def imp_room(self):
        sh = self.sheet('治疗室')
        if not sh:
            self.rep.add('治疗室', errors=['sheet 缺失'])
            return
        added = skipped = 0
        warns, errors = [], []
        for code, name in self.db.all(
                "SELECT f_id, f_room_name FROM hdms_bed_room_info WHERE f_tenant_id=%s "
                "AND IFNULL(f_delete_mark,0)=0", (TENANT,)):
            self.room_ids[name] = code
        idx = 0
        for row in sh.rows:
            name = sh.get(row, '治疗室名称')
            if not name:
                continue
            if name in self.room_ids:
                skipped += 1
                continue
            fid = SNOW.next()
            self.db.insert('hdms_bed_room_info', {
                'f_id': fid,
                'f_room_name': name,
                'f_treat_area': TREAT_AREA,
                'f_hosptial_area': HOSPITAL_AREA,
                'f_color': ROOM_COLORS[idx % len(ROOM_COLORS)],
                'f_description': sh.get(row, '备注'),
                'f_system_type': SYSTEM_TYPE,
                'f_name_pycode': '',
                'f_sort_code': int(re.sub(r'\D', '', sh.get(row, '排列顺序')) or (idx + 1)),
                'f_cd_flag': '0',
                'f_delete_mark': None,
                'f_creator_time': dt.datetime.now(),
                'f_tenant_id': TENANT,
            })
            self.room_ids[name] = fid
            idx += 1
            added += 1
        self.rep.add('治疗室', added, skipped, warns, errors)

    # ---------------- 9. 治疗区域（床位分组） ----------------
    def imp_group(self):
        sh = self.sheet('治疗区域')
        if not sh:
            self.rep.add('治疗区域', errors=['sheet 缺失'])
            return
        added = skipped = 0
        warns, errors = [], []
        for gid, gname in self.db.all(
                "SELECT f_id, f_group_name FROM hdms_bed_group_info WHERE f_tenant_id=%s",
                (TENANT,)):
            self.group_ids[gname] = gid
        idx = 0
        for row in sh.rows:
            name = sh.get(row, '分组名称')
            if not name:
                continue
            if name in self.group_ids:
                skipped += 1
                continue
            fid = SNOW.next()
            self.db.insert('hdms_bed_group_info', {
                'f_id': fid,
                'f_group_name': name,
                'f_hosptial_area': HOSPITAL_AREA,
                'f_description': sh.get(row, '备注'),
                'f_color': ROOM_COLORS[(idx + 3) % len(ROOM_COLORS)],
                'f_sort_code': int(re.sub(r'\D', '', sh.get(row, '排列顺序')) or (idx + 1)),
                'f_delete_mark': None,
                'f_tenant_id': TENANT,
            })
            self.group_ids[name] = fid
            idx += 1
            added += 1
        self.rep.add('治疗区域', added, skipped, warns, errors)

    def _group_for_bed(self, sh, row, bed_name: str, room_name: str) -> str:
        """床位归组以「治疗区域」列为准；列留空时才按治疗室兜底。"""
        gname = (sh.get(row, '治疗区域') or '').strip()
        if gname:
            return gname
        return ROOM_GROUP.get(room_name, '')

    # ---------------- 10. 床位 ----------------
    def imp_bed(self):
        sh = self.sheet('床位')
        if not sh:
            self.rep.add('床位', errors=['sheet 缺失'])
            return
        added = skipped = 0
        warns, errors = [], []
        exist = set()
        other_rooms = {}
        for fid, rname, bname in self.db.all(
                "SELECT b.f_id, r.f_room_name, b.f_bed_name FROM hdms_bed_device_info b "
                "LEFT JOIN hdms_bed_room_info r ON r.f_id=b.f_room_id "
                "WHERE IFNULL(b.f_delete_mark,0)=0 AND b.f_tenant_id=%s", (TENANT,)):
            exist.add((rname or '', bname or ''))
            other_rooms.setdefault(bname or '', set()).add(rname or '')
            self.bed_ids.setdefault(bname, fid)
        clash = 0
        fallback = 0
        default_group = next(iter(self.group_ids.values()), None)
        for row in sh.rows:
            bname = sh.get(row, '床位名称')
            rname = sh.get(row, '治疗室名称')
            if not bname:
                continue
            if (rname, bname) in exist:
                skipped += 1
                continue
            room_id = self.room_ids.get(rname)
            if not room_id:
                errors.append('%s 的治疗室「%s」不存在，请先导入治疗室' % (bname, rname))
                continue
            raw_group = (sh.get(row, '治疗区域') or '').strip()
            gname = self._group_for_bed(sh, row, bname, rname)
            if not raw_group:
                fallback += 1
            if gname and gname not in self.group_ids:
                if raw_group:      # 模板显式填了但库里没有 -> 真错误
                    errors.append('%s 的治疗区域「%s」不存在，请先导入治疗区域' % (bname, gname))
                    continue
                gname = ''         # 兜底名也不存在 -> 退回默认分组
            gid = self.group_ids.get(gname) or default_group
            if not gid:
                errors.append('%s 找不到可用的床位分组，请先导入治疗区域' % bname)
                continue
            m = re.search(r'(\d+)', bname)
            if bname in other_rooms and rname not in other_rooms[bname]:
                clash += 1
            fid = SNOW.next()
            self.db.insert('hdms_bed_device_info', {
                'f_id': fid,
                'f_room_id': room_id,
                'f_bed_name': bname,
                'f_hosptial_area': HOSPITAL_AREA,
                'f_group_id': gid,
                'f_name_pycode': '',
                'f_sort_code': int(m.group(1)) if m else 0,
                'f_delete_mark': None,
                'f_creator_time': dt.datetime.now(),
                'f_tenant_id': TENANT,
            })
            self.bed_ids.setdefault(bname, fid)
            exist.add((rname, bname))
            added += 1
        if fallback:
            warns.append('有 %d 张床位未填「治疗区域」，已按治疗室兜底分组，请核对' % fallback)
        if clash:
            warns.append('有 %d 张床位在库中「别的治疗室」已存在同名床位（不同治疗室允许同名，'
                         '但排班/上机选床时容易选错，建议核对是否要复用原床位）' % clash)
        self.rep.add('床位', added, skipped, warns, errors)

    # ---------------- 11. 透析机 ----------------
    def imp_equipment(self):
        sh = self.sheet('透析机')
        if not sh:
            self.rep.add('透析机', errors=['sheet 缺失'])
            return
        added = skipped = 0
        warns, errors = [], []
        existing = {(r[0] or '').lower(): r[0] for r in self.db.all(
            "SELECT f_equip_code FROM hdms_eq_equipment WHERE f_tenant_id=%s "
            "AND IFNULL(f_delete_mark,0)=0", (TENANT,))}
        # 型号 / 厂商：名称 → f_id（f_equip_type / f_factory_id 存的都是主键）
        if not self.eq_type_ids:
            for fid, tname, tkind in self.db.all(
                    "SELECT f_id, f_equip_name, f_equip_kind FROM hdms_dict_eq_type"):
                self.eq_type_ids[tname] = fid
                self.eq_type_kind[tname] = tkind
        if not self.factory_ids:
            for fid, fname in self.db.all(
                    "SELECT f_id, f_factory_name FROM hdms_dict_factory"):
                self.factory_ids[fname] = fid
        # f_equip_name 上有全局唯一索引，同型号多台机器必须错开名称
        used_names = {norm_name(r[0]) for r in self.db.all(
            "SELECT f_equip_name FROM hdms_eq_equipment")}
        name_freq = {}
        for r in sh.rows:
            n = norm_name(sh.get(r, '设备名称'))
            if n:
                name_freq[n] = name_freq.get(n, 0) + 1
        renamed = 0
        for row in sh.rows:
            name = sh.get(row, '设备名称')
            code = sh.get(row, '设备编号')
            if not name:
                continue
            # 设备编号留空时，按「名称末尾 -序号」自动补，没有序号则用排列顺序兜底
            if not code:
                m_code = re.search(r'-(\d+)$', name.strip())
                code = m_code.group(1) if m_code else (re.sub(r'\D', '', sh.get(row, '排列顺序')) or '')
            if code and code.lower() in existing:
                skipped += 1
                continue
            need_suffix = name_freq.get(norm_name(name), 1) > 1 or norm_name(name) in used_names
            equip_name = '%s-%s' % (name, code) if (need_suffix and code) else name
            if norm_name(equip_name) in used_names:
                equip_name = '%s-%s-%d' % (name, code or '', len(used_names) + 1)
            if equip_name != name:
                renamed += 1
            used_names.add(norm_name(equip_name))
            kind_name = sh.get(row, '设备类别')
            kind = self.dicts.code_by_name('EQUIP_KIND', kind_name) if kind_name else ''
            if not kind:
                kind = EQUIP_KIND_MAP.get(kind_name, '01')
                if kind_name and kind_name not in EQUIP_KIND_MAP:
                    warns.append('%s 的设备类别「%s」没匹配到，暂用 01=透析机' % (name, kind_name))
            state = sh.get(row, '设备状态')
            state_code = self.dicts.code_by_name('EQ_STATE', state) if state else ''
            if not state_code:
                state_code = '1'
            left = sh.get(row, '机位')
            if left not in ('L', 'R'):
                left = 'L'
            # 型号 / 厂商：模板填名称，库里存主键
            model_name = sh.get(row, '设备型号')
            type_id = self.eq_type_ids.get(model_name)
            if model_name and not type_id:
                warns.append('%s 的型号「%s」在「设备型号」表中不存在，f_equip_type 留空'
                             % (name, model_name))
            if model_name and type_id:
                tk = self.eq_type_kind.get(model_name)
                if tk and tk != kind:
                    warns.append('%s 的型号「%s」在型号表里是 %s，与「设备类别」%s 不一致'
                                 % (name, model_name,
                                    self.dicts.name_by_code('EQUIP_KIND', tk), kind_name))
            fac_name = sh.get(row, '制造厂商')
            fac_id = self.factory_ids.get(fac_name)
            if fac_name and not fac_id:
                warns.append('%s 的厂商「%s」在「制造厂商」表中不存在，f_factory_id 留空'
                             % (name, fac_name))
            eqid = SNOW.next()
            self.db.insert('hdms_eq_equipment', {
                'f_id': eqid,
                'f_equip_kind': kind,
                'f_equip_type': type_id or '',
                'f_equip_name': equip_name,
                'f_equip_code': code,
                'f_equip_spec': '',
                'f_factory_id': fac_id,
                'f_eq_state': state_code,
                'f_is_left': left,
                'f_hosptial_area': HOSPITAL_AREA,
                'f_name_pycode': '',
                'f_sort_code': int(re.sub(r'\D', '', sh.get(row, '排列顺序')) or 0),
                'f_delete_mark': None,
                'f_creator_time': dt.datetime.now(),
                'f_tenant_id': TENANT,
            })
            if code:
                existing[code.lower()] = code
            added += 1
        if renamed:
            warns.append('同型号多台设备已加「-编号」后缀区分，共 %d 台'
                         '（f_equip_name 上有唯一索引，不能重名）' % renamed)
        # 床位 ↔ 透析机：以「床位」sheet 的「透析机」列为准（床位 → 设备），
        # 「透析机」sheet 的「放置床位」是同一关联的反向写法，两边都填必须一致。
        bed_sh = self.sheet('床位')
        bed_to_machine = {}
        if bed_sh:
            for row in bed_sh.rows:
                bn = bed_sh.get(row, '床位名称')
                mn = bed_sh.get(row, '透析机')
                if bn and mn:
                    bed_to_machine[bn] = mn
        name_to_code = {}       # 设备名称 → 设备编号（模板里只填名称，库里按编号判重）
        for row in sh.rows:
            nm = sh.get(row, '设备名称')
            if not nm:
                continue
            code = sh.get(row, '设备编号')
            if not code:
                m_code = re.search(r'-(\d+)$', nm.strip())
                code = m_code.group(1) if m_code else (re.sub(r'\D', '', sh.get(row, '排列顺序')) or '')
            name_to_code[nm] = code
        code_to_bed = {}        # 设备编号 → 放置床位（反向着法）
        for row in sh.rows:
            bed_name = sh.get(row, '放置床位')
            nm = sh.get(row, '设备名称')
            if bed_name and nm:
                code_to_bed[name_to_code.get(nm, '')] = bed_name

        bound = 0
        owner = {}
        for bed_name, machine_name in bed_to_machine.items():
            code = name_to_code.get(machine_name)
            if not code:
                warns.append('床位「%s」填的透析机「%s」不在「透析机」sheet 里，未绑定'
                             % (bed_name, machine_name))
                continue
            owner.setdefault(code, []).append(bed_name)
            rev = code_to_bed.get(code)
            if rev and rev != bed_name:
                warns.append('设备编号 %s：床位表填「%s」、透析机表「放置床位」填「%s」，'
                             '两边不一致，已按床位表处理' % (code, bed_name, rev))
            if self._bind_bed_machine(code, bed_name, warns):
                bound += 1
        # 床位表空着、只在透析机表填了放置床位的，按透析机表兜底
        for code, bed_name in code_to_bed.items():
            if any(bed_name in v for v in owner.values()):
                continue
            if self._bind_bed_machine(code, bed_name, warns):
                bound += 1
                warns.append('设备编号 %s 只在「透析机」表的「放置床位」填了「%s」，已按该列绑定'
                             % (code, bed_name))
        for code, beds in owner.items():
            if len(beds) > 1:
                warns.append('设备编号 %s 同时被 %d 张床绑定（%s）：一台机器正常只对一张床，请核对'
                             % (code, len(beds), '、'.join(beds)))
        if bound:
            warns.append('已按「床位」表的「透析机」列回写 f_docu_id，共 %d 张床' % bound)
        self.rep.add('透析机', added, skipped, warns, errors)

    def _patient_id(self, name: str) -> str:
        """姓名 → 患者ID：先看本次导入缓存，再查库（同名多条则视为歧义返回空）。"""
        if name in self.patient_ids:
            return self.patient_ids[name]
        rows = self.db.all(
            "SELECT f_id FROM hdms_patient_info WHERE f_name=%s AND f_tenant_id=%s LIMIT 3",
            (name, TENANT))
        if len(rows) == 1:
            self.patient_ids[name] = rows[0][0]
            return rows[0][0]
        return ''

    def _bind_bed_machine(self, code: str, bed_name: str, warns: list) -> bool:
        """把设备编号对应的 f_id 写进床位 f_docu_id。"""
        eqid = self.db.scalar(
            "SELECT f_id FROM hdms_eq_equipment WHERE f_equip_code=%s "
            "AND IFNULL(f_delete_mark,0)=0 AND f_tenant_id=%s LIMIT 1", (code, TENANT))
        if not eqid:
            warns.append('设备编号 %s 未落库，跳过床位绑定' % code)
            return False
        bid = self.bed_ids.get(bed_name) or self.db.scalar(
            "SELECT f_id FROM hdms_bed_device_info WHERE f_bed_name=%s "
            "AND IFNULL(f_delete_mark,0)=0 AND f_tenant_id=%s LIMIT 1", (bed_name, TENANT))
        if not bid:
            warns.append('设备 %s 要绑的床位「%s」不存在，请先导入床位' % (code, bed_name))
            return False
        self.db.cur.execute(
            "UPDATE hdms_bed_device_info SET f_docu_id=%s WHERE f_id=%s", (eqid, bid))
        return True

    # ---------------- 12. 人员 ----------------
    def imp_user(self):
        sh = self.sheet('人员')
        if not sh:
            self.rep.add('人员', errors=['sheet 缺失'])
            return
        added = skipped = 0
        warns, errors = [], []
        # 角色
        for fid, code in self.db.all(
                "SELECT f_id, f_en_code FROM base_role WHERE IFNULL(f_delete_mark,0)=0"):
            self.role_ids[(code or '').lower()] = fid
        existing = {(r[0] or '').lower() for r in self.db.all(
            "SELECT f_account FROM base_user WHERE IFNULL(f_delete_mark,0)=0")}
        for row in sh.rows:
            name = sh.get(row, '姓名')
            account = sh.get(row, '登录账号')
            if not name or not account:
                continue
            if account.lower() in existing:
                skipped += 1
                continue
            job = sh.get(row, '职务')
            job_code, role_code = JOB_MAP.get(job, ('', ''))
            if job and not job_code:
                jc = self.dicts.code_by_name('JOB_TYPE', job)
                if jc:
                    job_code = jc
                    role_code = 'hs' if jc.startswith('2') else 'zzys'
                else:
                    warns.append('%s 的职务「%s」没匹配到字典，职务留空' % (name, job))
            role_id = self.role_ids.get(role_code or '') or ROLE_FALLBACK.get(role_code or '', '')
            if not role_id:
                warns.append('%s 没匹配到角色，f_role_id 留空（该账号登录后无菜单权限）' % name)
            dept = sh.get(row, '科室') or None
            plain = sh.get(row, '初始密码') or DEFAULT_USER_PASSWORD
            secret = SNOW.next()
            emp = sh.get(row, '工号')
            if emp and len(emp) > 5:
                errors.append('%s 的工号「%s」超过 5 位（f_employee_id 限长）' % (name, emp))
                continue
            self.db.insert('base_user', {
                'f_id': SNOW.next(),
                'f_account': account,
                'f_real_name': name,
                'f_quick_query': '',
                'f_nick_name': name,
                'f_employee_id': emp,
                'f_dept': dept,
                'f_job_type': json.dumps([job_code], ensure_ascii=False) if job_code else '',
                'f_role_id': role_id,
                'f_password': enc_password(plain, secret),
                'f_secretkey': secret,
                'f_enabled_mark': 1,
                'f_lock_mark': 0,
                'f_sort_code': int(re.sub(r'\D', '', sh.get(row, '排列顺序')) or 0),
                'f_delete_mark': None,
                'f_creator_time': dt.datetime.now(),
                'f_tenant_id': TENANT,
            })
            existing.add(account.lower())
            added += 1
        self.rep.add('人员', added, skipped, warns, errors)

    def _resolve_vas_code(self, vas_name: str) -> str:
        """患者表里的通路名 → hdms_dict_vas_access.f_vas_code。
        患者表常写简称（内瘘 / 颈静脉置管），需要逐级放宽匹配。"""
        if not vas_name:
            return ''
        if vas_name in self.vas_codes:
            return self.vas_codes[vas_name]
        alias = PATIENT_VAS_ALIAS.get(vas_name, '')
        if alias and alias in self.vas_codes:
            return self.vas_codes[alias]
        for vn, vc in self.vas_codes.items():
            if name_matches(vas_name, vn):
                return vc
        target = norm_name(alias or vas_name)
        # 病历里写「内瘘」，字典里是「动静脉内瘘」——用包含关系收口
        for vn, vc in self.vas_codes.items():
            if target and (target in norm_name(vn) or norm_name(vn) in target):
                return vc
        return ''

    # ---------------- 13. 患者 ----------------
    def imp_patient(self):
        sh = self.sheet('患者-基本信息')
        if not sh:
            self.rep.add('患者-基本信息', errors=['sheet 缺失'])
            return
        added = skipped = 0
        warns, errors = [], []
        seq = self.db.scalar(
            "SELECT MAX(CAST(f_patient_code AS UNSIGNED)) FROM hdms_patient_info "
            "WHERE f_patient_code REGEXP '^[0-9]+$'", default=0) or 0
        # 库中已占用的患者编号，模板里填了就直接用（不撞号），没填才自增
        used_codes = set()
        for r0 in self.db.all(
                "SELECT f_patient_code FROM hdms_patient_info "
                "WHERE f_patient_code IS NOT NULL AND f_patient_code<>''"):
            used_codes.add(str(r0[0]))
        for row in sh.rows:
            name = sh.get(row, '姓名')
            idno = sh.get(row, '证件号码')
            if not name:
                continue
            if idno:
                old = self.db.one("SELECT f_id FROM hdms_patient_info WHERE f_id_no=%s", (idno,))
                if old:
                    self.patient_ids[name] = old[0]
                    skipped += 1
                    continue
            birthday, sex_from_id = parse_id_card(idno)
            bday_cell = sh.get(row, '生日')
            if bday_cell:
                m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})', bday_cell)
                if m:
                    birthday = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                else:
                    warns.append('%s 的生日「%s」无法解析，改用证件号' % (name, bday_cell))
            if birthday is None:
                errors.append('%s 证件号 %r 无法解析生日，且生日列为空' % (name, idno))
                continue
            sex = self.dicts.code_by_name('sex', sh.get(row, '性别'))
            if not sex:
                sex = sex_from_id or '9'
            nation = self.dicts.code_by_name('Nation', sh.get(row, '民族'), fuzzy=True)
            if not nation and sh.get(row, '民族'):
                warns.append('%s 的民族「%s」没匹配到，暂用 01=汉族' % (name, sh.get(row, '民族')))
                nation = '01'
            payment = self.dicts.code_by_name('PAYMENT_MODE', sh.get(row, '付费方式'), fuzzy=True)
            blood = self.dicts.code_by_name('BLOOD_TYPE', sh.get(row, '血型'), fuzzy=True)
            marital = self.dicts.code_by_name('MARITAL_STATUS', sh.get(row, '婚否'))
            source = self.dicts.code_by_name('SOURCE', sh.get(row, '病人来源'), fuzzy=True)
            state = self.dicts.code_by_name('TREAT_STATE', sh.get(row, '治疗状态'), fuzzy=True)
            # 证件类别：默认身份证，填了名称就换编码
            idtype = self.dicts.code_by_name('IDENTITY_TYPE', sh.get(row, '证件类别')) or ID_TYPE_ID_CARD
            # 患者编号：模板填了就用，库中已占用则退回自增
            code = sh.get(row, '患者编号')
            if code and code in used_codes:
                warns.append('%s 的患者编号 %s 在库中已存在，改用自增编号'
                             % (name, code))
                code = ''
            if not code:
                seq += 1
                while str(seq) in used_codes:
                    seq += 1
                code = str(seq)
            used_codes.add(code)
            if code.isdigit():
                seq = max(seq, int(code))
            fid = SNOW.next()
            pdata = {
                'f_id': fid,
                'f_patient_code': code,
                'f_name': name,
                'f_patient_alias': sh.get(row, '别名') or None,
                'f_patient_docuid': sh.get(row, 'ID号') or None,
                'f_medical_rec_id': sh.get(row, '病历号') or None,
                'f_case_record_id': sh.get(row, '病志号') or None,
                'f_his_patient_id': sh.get(row, 'his患者编号') or None,
                'f_sex': sex,
                'f_nation': nation or None,
                'f_identity_type': idtype,
                'f_id_no': idno or '',
                'f_birthday': birthday.strftime('%Y-%m-%d'),
                'f_age': calc_age(birthday),
                'f_marital_status': marital or None,
                'f_citizenship': 'CN',
                'f_payment_mode': payment or None,
                'f_blood_type': blood or None,
                'f_tel': sh.get(row, '联系电话') or None,
                'f_treat_state': state or '1',
                'f_first_treat_mode': '',
                'f_diagnosis': DEFAULT_PATIENT_DIAGNOSIS,
                'f_cd_flag': '0',
                'f_high_risk': '0',
                'f_temp_patient': '0',
                'f_hosptial_area': HOSPITAL_AREA,
                'f_system_type': SYSTEM_TYPE,
                'f_sort_code': seq,
                'f_creator_time': dt.datetime.now(),
                'f_tenant_id': TENANT,
            }
            # f_source 是 NOT NULL 但库里有默认值 1（门诊），为空时整列不写，
            # 交给 MySQL 默认值；写 NULL 反而会报 1048
            if source:
                pdata['f_source'] = source
            self.db.insert('hdms_patient_info', pdata)
            self.patient_ids[name] = fid
            added += 1
            # 血管通路
            vas_name = sh.get(row, '血管通路名称') or sh.get(row, '通路位置')
            if vas_name:
                code = self._resolve_vas_code(vas_name)
                if not code:
                    warns.append('%s 的通路「%s」在血管通路类型里找不到，未建通路记录'
                                 % (name, vas_name))
                else:
                    self.db.insert('hdms_patient_vas_access', {
                        'f_id': SNOW.next(),
                        'f_patient_id': fid,
                        'f_vas_code': code,
                        'f_fistula_position': DEFAULT_VAS_POSITION,
                        'f_fistula_location': DEFAULT_VAS_LOCATION,
                        'f_start_date': dt.date.today().strftime('%Y-%m-%d'),
                        'f_stop_flag': '0',
                        'f_coexist': '',
                        'f_creator_time': dt.datetime.now(),
                        'f_tenant_id': TENANT,
                    })
            # 联系人
            contact = sh.get(row, '联系人')
            if contact:
                tel = sh.get(row, '联系电话')
                rel = self.dicts.code_by_name('RELATION', sh.get(row, '与联系人关系'))
                if not rel:
                    rel = '8'   # 其他
                if not tel:
                    warns.append('%s 的联系人「%s」因缺联系电话未写入（f_tel 非空）'
                                 % (name, contact))
                else:
                    self.db.insert('hdms_patient_contact_person', {
                        'f_id': SNOW.next(),
                        'f_patient_id': fid,
                        'f_contact_name': contact,
                        'f_tel': tel,
                        'f_relation': rel,
                        'f_creator_time': dt.datetime.now(),
                        'f_tenant_id': TENANT,
                    })
        self.rep.add('患者-基本信息', added, skipped, warns, errors)

    # ---------------- 14/15/16. 空表 ----------------
    # ---------------- 18. 患者-治疗方案 ----------------
    def imp_treat_plan(self):
        sh = self.sheet('患者-治疗方案')
        if not sh:
            self.rep.add('患者-治疗方案', errors=['sheet 缺失'])
            return
        added = skipped = 0
        warns, errors = [], []
        for row in sh.rows:
            rn = row.get('__row__')
            pname = sh.get(row, '患者姓名')
            plan_name = sh.get(row, '计划名称')
            if not pname and not plan_name:
                continue
            if not pname or not plan_name:
                errors.append('第 %s 行：患者姓名、计划名称都是必填' % rn)
                continue
            pid = self._patient_id(pname)
            if not pid:
                errors.append('第 %s 行：患者「%s」在库中不存在或重名，请先导入「患者-基本信息」'
                              % (rn, pname))
                continue
            try:
                cycle = int(re.sub(r'\D', '', sh.get(row, '周期(周)')) or 0)
                number = int(re.sub(r'\D', '', sh.get(row, '次数')) or 0)
            except ValueError:
                cycle = number = 0
            if cycle < 1 or number < 1:
                errors.append('%s / %s：周期(周)、次数都必须是正整数' % (pname, plan_name))
                continue
            if number > cycle * 7:
                errors.append('%s / %s：次数 %d 超过 周期 %d 周内最多 %d 次'
                              % (pname, plan_name, number, cycle, cycle * 7))
                continue
            try:
                start = to_date(row.get('开始日期'))
                stop = to_date(row.get('终止日期'))
            except ValueError as e:
                errors.append('%s / %s：%s' % (pname, plan_name, e))
                continue
            if not start:
                errors.append('%s / %s：开始日期必填（f_start_date 非空）' % (pname, plan_name))
                continue
            if stop and stop < start:
                errors.append('%s / %s：终止日期 %s 早于开始日期 %s' % (pname, plan_name, stop, start))
                continue
            m = re.match(r'^(\d+)\s*周\s*(\d+)\s*次$', norm_name(plan_name))
            if m and (int(m.group(1)) != cycle or int(m.group(2)) != number):
                warns.append('%s / %s：计划名称写的是 %s周%s次，但周期=%d、次数=%d，请核对'
                             % (pname, plan_name, m.group(1), m.group(2), cycle, number))
            old = self.db.scalar(
                "SELECT f_id FROM hdms_treat_plan WHERE f_patient_id=%s AND f_plan_name=%s "
                "AND f_tenant_id=%s LIMIT 1", (pid, plan_name, TENANT))
            if old:
                self.plan_meta[(pname, plan_name)] = (old, cycle, number)
                skipped += 1
                continue
            fid = SNOW.next()
            self.db.insert('hdms_treat_plan', {
                'f_id': fid,
                'f_patient_id': pid,
                'f_hosptial_area': HOSPITAL_AREA,
                'f_plan_name': plan_name,
                'f_cycle': cycle,
                'f_number': number,
                'f_start_date': start,
                'f_generate_date': start + ' 00:00:00',
                'f_stop_date': stop or None,
                'f_auto_generate': yes_no_char(sh.get(row, '自动生成预约'), '1'),
                'f_generate_mode': gen_mode_char(sh.get(row, '生成模式'), '1'),
                'f_sort_code': int(re.sub(r'\D', '', sh.get(row, '序号')) or 0),
                'f_enabled_mark': 1,
                'f_creator_time': dt.datetime.now(),
                'f_tenant_id': TENANT,
            })
            self.plan_meta[(pname, plan_name)] = (fid, cycle, number)
            added += 1
        self.rep.add('患者-治疗方案', added, skipped, warns, errors)

    # ---------------- 19. 患者排班表 ----------------
    def _load_schedule_refs(self):
        """排班要用的名称→主键/编码，整批查一次。"""
        if not self.sched_codes:
            for code, name in self.db.all(
                    "SELECT f_schedule_code, f_schedule_name FROM hdms_dict_schedule "
                    "WHERE f_tenant_id=%s AND IFNULL(f_delete_mark,0)=0", (TENANT,)):
                self.sched_codes[name] = code
        if not self.room_ids:
            for fid, name in self.db.all(
                    "SELECT f_id, f_room_name FROM hdms_bed_room_info "
                    "WHERE f_tenant_id=%s AND IFNULL(f_delete_mark,0)=0", (TENANT,)):
                self.room_ids[name] = fid
        if not self.bed_room:
            for fid, bname, rname in self.db.all(
                    "SELECT b.f_id, b.f_bed_name, r.f_room_name FROM hdms_bed_device_info b "
                    "LEFT JOIN hdms_bed_room_info r ON r.f_id=b.f_room_id "
                    "WHERE IFNULL(b.f_delete_mark,0)=0 AND b.f_tenant_id=%s", (TENANT,)):
                self.bed_ids.setdefault(bname, fid)
                self.bed_room[bname] = rname or ''
        exp = {}
        for code, name, attr in self.db.all(
                "SELECT f_exp_code, f_exp_name, f_exp_attr FROM hdms_dict_exp_info "
                "WHERE f_tenant_id=%s AND IFNULL(f_delete_mark,0)=0", (TENANT,)):
            exp.setdefault(name, (code, attr or ''))
        mode_code = {}
        mode_sh = self.sheet('治疗模式')
        if mode_sh:
            for row in mode_sh.rows:
                nm = mode_sh.get(row, '治疗模式名称')
                code = mode_sh.get(row, '编号')
                if nm and code:
                    mode_code[nm] = code
        if not mode_code:
            for code, name in self.db.all(
                    "SELECT f_en_code, f_full_name FROM base_dictionary_data "
                    "WHERE f_dictionary_type_code='TREAT_MODE' AND f_tenant_id=%s", (TENANT,)):
                mode_code[name] = code
        return exp, mode_code

    def imp_plan_schedule(self):
        sh = self.sheet('患者排班表')
        if not sh:
            self.rep.add('患者排班表', errors=['sheet 缺失'])
            return
        added = skipped = 0
        warns, errors = [], []
        exp, mode_code = self._load_schedule_refs()
        if not self.plan_meta:
            for pid, pname, pplan, cyc, num in self.db.all(
                    "SELECT t.f_id, p.f_name, t.f_plan_name, t.f_cycle, t.f_number "
                    "FROM hdms_treat_plan t LEFT JOIN hdms_patient_info p ON p.f_id=t.f_patient_id "
                    "WHERE t.f_tenant_id=%s AND IFNULL(t.f_enabled_mark,1)=1", (TENANT,)):
                self.plan_meta[(pname, pplan)] = (pid, cyc, num)
        # 库里已占用的 (周次, 星期, 班次, 床位)
        occupied = {}
        for wnum, wday, code, bed, who in self.db.all(
                "SELECT s.f_week_num, s.f_week_day, s.f_schedule_code, s.f_bed_id, p.f_name "
                "FROM hdms_treat_plan_schedule s "
                "LEFT JOIN hdms_treat_plan t ON t.f_id=s.f_plan_id "
                "LEFT JOIN hdms_patient_info p ON p.f_id=t.f_patient_id "
                "WHERE s.f_tenant_id=%s AND IFNULL(t.f_enabled_mark,1)=1 "
                "AND IFNULL(s.f_enabled_mark,1)=1 AND IFNULL(s.f_bed_id,'')<>''", (TENANT,)):
            occupied[(wnum, wday, code, bed)] = who or '其他患者'
        plan_rows = {}
        in_rows = {}
        slot_seen = {}
        for row in sh.rows:
            rn = row.get('__row__')
            pname = sh.get(row, '患者姓名')
            if not pname:
                continue
            plan_name = sh.get(row, '计划名称')
            tag = '%s / %s' % (pname, plan_name or '未填计划名称')
            meta = self.plan_meta.get((pname, plan_name))
            if not meta:
                errors.append('第 %s 行 %s：找不到对应的治疗计划，请先导入「患者-治疗方案」'
                              % (rn, tag))
                continue
            plan_id, cycle, number = meta
            plan_rows[(pname, plan_name)] = plan_rows.get((pname, plan_name), 0) + 1
            wday = to_week_day(row.get('星期几'))
            if not wday:
                errors.append('第 %s 行 %s：星期几「%s」认不出，填 周一~周日'
                              % (rn, tag, sh.get(row, '星期几')))
                continue
            wnum_raw = re.sub(r'\D', '', sh.get(row, '第几周'))
            wnum = int(wnum_raw) if wnum_raw else 1
            if wnum < 1:
                errors.append('第 %s 行 %s：第几周必须从 1 开始' % (rn, tag))
                continue
            if wnum > cycle:
                errors.append('第 %s 行 %s：第几周 %d 超出计划周期 %d 周'
                              % (rn, tag, wnum, cycle))
                continue
            sc_name = sh.get(row, '班次名称')
            scode = self.sched_codes.get(sc_name)
            if not scode:
                errors.append('第 %s 行 %s：班次「%s」不存在，请先导入班次'
                              % (rn, tag, sc_name))
                continue
            bed_name = sh.get(row, '床位名称')
            bed_id = ''
            if bed_name:
                bed_id = self.bed_ids.get(bed_name) or ''
                if not bed_id:
                    errors.append('第 %s 行 %s：床位「%s」不存在，请先导入床位'
                                  % (rn, tag, bed_name))
                    continue
            room_name = sh.get(row, '治疗室名称') or self.bed_room.get(bed_name, '')
            room_id = self.room_ids.get(room_name, '')
            if not room_id:
                errors.append('第 %s 行 %s：治疗室「%s」不存在（床位「%s」也没带出治疗室）'
                              % (rn, tag, room_name, bed_name))
                continue
            mode_name = sh.get(row, '治疗模式')
            mode = mode_code.get(mode_name, mode_name)
            if mode_name and mode_name not in mode_code:
                warns.append('第 %s 行 %s：治疗模式「%s」不在「治疗模式」表里，按原值写入'
                             % (rn, tag, mode_name))
            filters = []
            for col, want, label in (('透析器', '01', '透析器'), ('灌流器', '02', '灌流器')):
                fname = sh.get(row, col)
                if not fname:
                    filters.append('')
                    continue
                hit = exp.get(fname)
                if not hit:
                    errors.append('第 %s 行 %s：%s「%s」不在「透析滤器」表里'
                                  % (rn, tag, label, fname))
                    filters.append('')
                    continue
                if hit[1] and hit[1] != want:
                    warns.append('第 %s 行 %s：%s列填的「%s」在滤器表里是 %s，类型不匹配'
                                 % (rn, tag, label, fname,
                                    self.dicts.name_by_code('EXP_ATTR', hit[1]) or hit[1]))
                filters.append(hit[0])
            # 幂等：这一条已落库就直接跳过。必须放在冲突判定之前，
            # 否则第二次导入时「自己占的床位」会被自己判成冲突。
            old = self.db.scalar(
                "SELECT f_id FROM hdms_treat_plan_schedule WHERE f_plan_id=%s AND f_week_num=%s "
                "AND f_week_day=%s AND f_schedule_code=%s AND IFNULL(f_bed_id,'')=%s "
                "AND f_tenant_id=%s LIMIT 1",
                (plan_id, wnum, wday, scode, bed_id, TENANT))
            if old:
                skipped += 1
                continue

            # 冲突：同床同班次同周次同星期
            key = (wnum, wday, scode, bed_id)
            if bed_id:
                if key in in_rows:
                    errors.append('第 %s 行 %s：与第 %s 行排床冲突（%d周 %s %s %s）'
                                  % (rn, tag, in_rows[key], wnum, WEEK_NAME_BY_DAY.get(wday, wday),
                                     sc_name, bed_name))
                    continue
                if key in occupied:
                    errors.append('第 %s 行 %s：床位冲突，%s 已在 %d周 %s %s 占用 %s'
                                  % (rn, tag, occupied[key], wnum,
                                     WEEK_NAME_BY_DAY.get(wday, wday), sc_name, bed_name))
                    continue
                in_rows[key] = rn
            # 冲突：同一患者同一周次同一天同一班次排了两张床
            pkey = (pname, wnum, wday, scode)
            if pkey in slot_seen:
                errors.append('第 %s 行 %s：同一患者在 %d周 %s %s 排了两条（另见第 %s 行）'
                              % (rn, tag, wnum, WEEK_NAME_BY_DAY.get(wday, wday), sc_name,
                                 slot_seen[pkey]))
                continue
            slot_seen[pkey] = rn
            self.db.insert('hdms_treat_plan_schedule', {
                'f_id': SNOW.next(),
                'f_plan_id': plan_id,
                'f_schedule_code': scode,
                'f_week_day': wday,
                'f_week_num': wnum,
                'f_bed_id': bed_id or None,
                'f_treat_mode': mode,
                'f_dialysis_filter': filters[0],
                'f_dialysis_filter2': filters[1],
                'f_room_id': room_id,
                'f_enabled_mark': 1,
                'f_tenant_id': TENANT,
            })
            added += 1
        for k, n in plan_rows.items():
            meta = self.plan_meta.get(k)
            if meta and n != meta[2]:
                warns.append('%s / %s：排班明细 %d 条，计划「次数」是 %d，请核对'
                             % (k[0], k[1], n, meta[2]))
        for k, meta in self.plan_meta.items():
            if k not in plan_rows:
                warns.append('%s / %s：计划在库/模板里存在，但排班表没有任何明细' % k)
        self.rep.add('患者排班表', added, skipped, warns, errors)

    def imp_empty(self, sheet_name):
        sh = self.sheet(sheet_name)
        if not sh or not sh.rows:
            self.rep.add(sheet_name, 0, 0, ['模板中无数据，跳过'], [])
            return
        self.rep.add(sheet_name, 0, 0, ['有数据但脚本未实现该表，已跳过，请手工处理'], [])

    def imp_fee_tc(self):
        self.imp_empty('套餐')


# ============================================================================
# 八、主流程
# ============================================================================

DISPATCH = {
    '字典分类': 'imp_dict_type',
    '字典值': 'imp_dict_value',
    '制造厂商': 'imp_factory',
    '设备型号': 'imp_eq_type',
    '治疗模式': 'imp_treat_mode',
    '保险类型': 'imp_payment_mode',
    '抗凝剂种类': 'imp_anticoagulant',
    '血管通路类型': 'imp_vas',
    '透析液': 'imp_dialyzate',
    '透析滤器': 'imp_exp_info',
    '班次': 'imp_schedule',
    '治疗室': 'imp_room',
    '治疗区域': 'imp_group',
    '床位': 'imp_bed',
    '透析机': 'imp_equipment',
    '人员': 'imp_user',
    '患者-基本信息': 'imp_patient',
    '套餐': 'imp_fee_tc',
    '患者-治疗方案': 'imp_treat_plan',
    '患者排班表': 'imp_plan_schedule',
}


def parse_args():
    p = argparse.ArgumentParser(description='jsbos-hdms 基础数据一键导入')
    p.add_argument('--xlsx', default=DEFAULT_XLSX, help='模板路径')
    p.add_argument('--execute', action='store_true', help='真正写库（默认只演练并回滚）')
    p.add_argument('--only', default='', help='只导指定表，逗号分隔，如 治疗室,床位')
    p.add_argument('--skip', default='', help='跳过的表，逗号分隔')
    p.add_argument('--host', default=DB['host'])
    p.add_argument('--port', type=int, default=DB['port'])
    p.add_argument('--user', default=DB['user'])
    p.add_argument('--password', default=DB['password'])
    p.add_argument('--db', default=DB['database'])
    p.add_argument('--tenant', default=TENANT)
    return p.parse_args()


def main():
    global TENANT
    args = parse_args()
    if args.tenant:
        TENANT = args.tenant

    only = [x.strip() for x in args.only.split(',') if x.strip()]
    skip = [x.strip() for x in args.skip.split(',') if x.strip()]
    plan = [t for t in IMPORT_ORDER if (not only or t in only) and t not in skip]

    print('模板  :', args.xlsx)
    print('目标库: %s@%s:%s/%s  租户=%s' % (args.user, args.host, args.port, args.db, TENANT))
    print('模式  :', '执行并提交' if args.execute else '演练（执行后回滚，不落库）')
    print('范围  :', ', '.join(plan))
    print()

    book = load_book(args.xlsx)
    cfg = dict(host=args.host, port=args.port, user=args.user,
               password=args.password, database=args.db, charset='utf8mb4')
    db = DB2(cfg, dry_run=not args.execute)
    rep = Reporter()
    imp = Importer(db, book, rep)

    ok = True
    try:
        for name in plan:
            fn = DISPATCH.get(name)
            if not fn:
                rep.add(name, errors=['脚本未实现该表'])
                continue
            try:
                if fn == 'imp_empty':
                    getattr(imp, fn)(name)
                else:
                    getattr(imp, fn)()
                print('  ✓ %s' % name)
            except Exception as e:
                ok = False
                rep.add(name, errors=['%s: %s' % (type(e).__name__, e)])
                print('  ✗ %s -> %s' % (name, e))
                if os.environ.get('IMPORT_TRACE'):
                    traceback.print_exc()
                break
    finally:
        db.finish(ok)

    print(rep.render())
    ta, ts, tw, te = rep.summary()
    if args.execute and ok:
        print('\n已提交：新增 %d 条，跳过 %d 条（已存在）' % (ta, ts))
    elif not args.execute:
        print('\n演练结束：预计新增 %d 条，跳过 %d 条；未写库。确认后加 --execute 执行。' % (ta, ts))
    else:
        print('\n执行失败，已整体回滚，库未改动。')
    return 0 if ok and te == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
