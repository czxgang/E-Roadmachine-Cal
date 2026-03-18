import streamlit as st
import datetime

class ElectricMachine:
    # 类和之前一样，不需要修改
    def __init__(self, battery_capacity_kwh, initial_soc_percent):
        self.capacity = battery_capacity_kwh
        self.soc = initial_soc_percent / 100 * self.capacity
        self.is_running = False
        self.start_time = None
        self.total_energy_consumed = 0.0

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.start_time = datetime.datetime.now()
            return f"机器启动于 {self.start_time}"
        else:
            return "机器已经在运行中"

    def stop(self, avg_power_kw):
        if self.is_running:
            end_time = datetime.datetime.now()
            duration = (end_time - self.start_time).total_seconds() / 3600
            energy = avg_power_kw * duration
            self.total_energy_consumed += energy
            self.soc -= energy
            self.is_running = False
            return (f"机器停止于 {end_time}\n"
                    f"本次运行时长: {duration:.2f} 小时\n"
                    f"本次能耗: {energy:.2f} kWh\n"
                    f"当前剩余电量: {self.soc:.2f} kWh ({self.soc/self.capacity*100:.1f}%)")
        else:
            return "机器未运行"

    def status(self):
        status_lines = []
        if self.is_running:
            now = datetime.datetime.now()
            duration = (now - self.start_time).total_seconds() / 3600
            status_lines.append(f"正在运行，已运行 {duration:.2f} 小时")
        status_lines.append(f"累计能耗: {self.total_energy_consumed:.2f} kWh")
        status_lines.append(f"剩余电量: {self.soc:.2f} kWh ({self.soc/self.capacity*100:.1f}%)")
        return "\n".join(status_lines)

# ---------- Streamlit 界面 ----------
st.set_page_config(page_title="电动工程机械能耗监控", layout="centered")
st.title("🚜 电动工程机械能耗监控")

# 初始化 session_state 中的 machine 对象
if "machine" not in st.session_state:
    # 默认电池容量 200 kWh，初始电量 80%
    st.session_state.machine = ElectricMachine(
        battery_capacity_kwh=200.0,
        initial_soc_percent=80.0
    )

machine = st.session_state.machine

# 侧边栏显示机器参数
with st.sidebar:
    st.header("机器参数")
    capacity = st.number_input("电池容量 (kWh)", min_value=1.0, value=200.0, step=1.0)
    initial_soc = st.number_input("初始电量 (%)", min_value=0.0, max_value=100.0, value=80.0, step=1.0)
    if st.button("重置机器"):
        st.session_state.machine = ElectricMachine(capacity, initial_soc)
        st.rerun()

# 主界面：显示当前状态
st.subheader("当前状态")
status_text = machine.status()
st.text(status_text)

# 操作按钮
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("▶️ 启动"):
        msg = machine.start()
        st.success(msg)
with col2:
    if st.button("⏹️ 停止"):
        # 停止时需要输入平均功率，可以用一个弹出输入或数字输入
        # 为了简单，这里在侧边栏或主界面加一个输入框
        pass  # 稍后处理
with col3:
    if st.button("🔄 刷新状态"):
        st.rerun()

# 停止操作需要输入功率，放在下面单独区域
st.subheader("停止机器")
avg_power = st.number_input("本次运行平均功率 (kW)", min_value=0.0, value=50.0, step=1.0)
if st.button("停止并计算能耗"):
    msg = machine.stop(avg_power)
    st.info(msg)
    st.rerun()  # 刷新状态显示