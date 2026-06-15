# coding: utf-8
from sqlalchemy import CHAR, Column, DateTime, Float, String, Text, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, LONGBLOB, LONGTEXT, TINYINT, VARCHAR
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class AioDatum(Base):
    __tablename__ = 'aio_data'

    taskId = Column(String(64), primary_key=True, unique=True, comment='任务ID')
    RBData = Column(LONGTEXT)
    probCount = Column(LONGTEXT)
    totalTime = Column(BIGINT(100), server_default=text("0"))
    queueTime = Column(BIGINT(100), server_default=text("0"))
    compileTime = Column(BIGINT(100), server_default=text("0"))
    amendTime = Column(BIGINT(100), server_default=text("0"))
    aioExecuteTime = Column(BIGINT(100), server_default=text("0"))
    aioCompileTime = Column(BIGINT(100), server_default=text("0"))
    aioPendingTime = Column(BIGINT(100), server_default=text("0"))
    aioMeasureTime = Column(BIGINT(100), server_default=text("0"))
    aioPostProcessTime = Column(BIGINT(100), server_default=text("0"))
    aioTimeStamp = Column(String(256), server_default=text("'\"\"'"))
    measureQubitSize = Column(LONGTEXT)


class ChipDatum(Base):
    __tablename__ = 'chip_data'

    chipId = Column(INTEGER(11), primary_key=True)
    qubitsUpdateTime = Column(LONGTEXT, nullable=False)


class ChipExectime(Base):
    __tablename__ = 'chip_exectime'
    __table_args__ = {'comment': '芯片独占时间表'}

    id = Column(BIGINT(20), primary_key=True, comment='id')
    chip_id = Column(BIGINT(20), nullable=False, comment='芯片ID')
    start_time = Column(DateTime, comment='独占开始时间')
    end_time = Column(DateTime, comment='独占结束时间')


class ChipFidelityDatum(Base):
    __tablename__ = 'chip_fidelity_data'

    id = Column(INTEGER(11), primary_key=True)
    task_id = Column(String(256))
    state = Column(INTEGER(11), server_default=text("-1"))
    chip_id = Column(String(256))
    label = Column(INTEGER(11), server_default=text("1"))
    expand_task_num = Column(INTEGER(11))
    update_time = Column(BIGINT(100))
    ir_type = Column(String(256))
    fidelity_data = Column(LONGTEXT)
    schedule = Column(INTEGER(11), server_default=text("0"))
    start_time = Column(BIGINT(100))
    end_time = Column(BIGINT(100))


class ClopsTest(Base):
    __tablename__ = 'clops_test'
    __table_args__ = {'comment': 'clops测试表'}

    id = Column(BIGINT(20), primary_key=True, comment='主键ID')
    max_batch_limits = Column(BIGINT(20), comment='最大批次限制')
    circuits_num = Column(BIGINT(20), comment='线路数')
    layers_num = Column(BIGINT(20), comment='层数')
    iterations = Column(BIGINT(20), comment='迭代数')
    chip_id = Column(BIGINT(20), comment='芯片id')
    is_amend = Column(TINYINT(1), comment='是否修正')
    is_mapping = Column(TINYINT(1), comment='是否开启映射')
    is_optimization = Column(TINYINT(1), comment='是否开启线路优化')
    clops = Column(Float(asdecimal=True), comment='clops结果')
    status = Column(BIGINT(4), comment='状态：1.已提交；2.异常；3.已完成')
    error_info = Column(String(255), comment='异常信息')
    start_time = Column(DateTime, nullable=False, comment='开始时间')
    end_time = Column(DateTime, comment='结束时间')


class CloudUserSK(Base):
    __tablename__ = 'cloud_user_SK'

    cloud_user_id = Column(INTEGER(11), primary_key=True)
    sk = Column(LONGTEXT)
    pk_id = Column(String(64))
    secret_key = Column(LONGTEXT)
    IV = Column(LONGTEXT)


class JobChipMapping(Base):
    __tablename__ = 'job_chip_mapping'
    __table_args__ = {'comment': '定时任务与芯片映射表'}

    id = Column(INTEGER(11), primary_key=True, comment='主键ID')
    job_id = Column(String(50), nullable=False, unique=True, comment='定时任务ID')
    chip_ids = Column(Text, comment='芯片ID列表，以逗号分隔')
    create_time = Column(DateTime, server_default=text("current_timestamp()"), comment='创建时间')
    update_time = Column(DateTime, server_default=text("current_timestamp() ON UPDATE current_timestamp()"), comment='更新时间')


class M3SampleInfo(Base):
    __tablename__ = 'm3_sample_info'

    info_id = Column(INTEGER(11), primary_key=True)
    chip_name = Column(String(45))
    label = Column(TINYINT(4))
    status = Column(String(45))
    start_time = Column(BIGINT(20))
    end_time = Column(BIGINT(20))


class ProfCompensateAngle(Base):
    __tablename__ = 'prof_compensate_angle'

    id = Column(INTEGER(11), primary_key=True)
    task_id = Column(String(64), nullable=False)
    state = Column(INTEGER(11), server_default=text("1"))
    chip_id = Column(String(64), nullable=False)
    label = Column(INTEGER(11), nullable=False)
    qubits = Column(String(64))
    depth = Column(INTEGER(11))
    check_time = Column(BIGINT(20))
    err_info = Column(String(64))
    compensate_angle = Column(String(1024))


class ProfilingQprog(Base):
    __tablename__ = 'profiling_qprog'

    id = Column(INTEGER(11), primary_key=True)
    qprog = Column(LONGTEXT, nullable=False)
    qprog_qubit_num = Column(INTEGER(11))
    qprog_depth = Column(INTEGER(11))


class ProfilingResult(Base):
    __tablename__ = 'profiling_result'

    id = Column(String(256), primary_key=True)
    profiling_type = Column(INTEGER(11), server_default=text("0"))
    task_num = Column(INTEGER(11))
    state = Column(INTEGER(11))
    start_time = Column(BIGINT(20))
    end_time = Column(BIGINT(20))
    result = Column(LONGTEXT)


class ProfilingTask(Base):
    __tablename__ = 'profiling_task'

    id = Column(INTEGER(11), primary_key=True)
    state = Column(INTEGER(11))
    start_time = Column(BIGINT(100), server_default=text("0"))
    end_time = Column(BIGINT(100), server_default=text("0"))
    profiling_desc = Column(String(1024), server_default=text("'0'"))
    is_develop = Column(TINYINT(8), server_default=text("0"))


class ProfilingTaskResult(Base):
    __tablename__ = 'profiling_task_result'

    id = Column(INTEGER(11), primary_key=True)
    profiling_qprog_id = Column(INTEGER(11))
    profiling_task_id = Column(INTEGER(11))
    state = Column(INTEGER(11), server_default=text("0"))
    start_time = Column(BIGINT(20))
    end_time = Column(BIGINT(20))
    profiling_flag = Column(String(45))
    min_cpu_usage = Column(Float(asdecimal=True))
    max_cpu_usage = Column(Float(asdecimal=True))
    min_mem_usage = Column(Float(asdecimal=True))
    max_mem_usage = Column(Float(asdecimal=True))
    min_throughput = Column(INTEGER(11))
    max_throughput = Column(INTEGER(11))
    min_response_time = Column(BIGINT(20))
    max_response_time = Column(BIGINT(20))
    max_avg_compile_time = Column(BIGINT(20))
    min_avg_compile_time = Column(BIGINT(20))
    cur_quantum_utilization = Column(Float(asdecimal=True))
    max_quantum_utilization = Column(Float(asdecimal=True))
    cpu_kernel = Column(INTEGER(11))
    memory = Column(INTEGER(11))
    disk_type = Column(INTEGER(11))
    flag = Column(String(30))


class ProfilingTimeConsume(Base):
    __tablename__ = 'profiling_time_consume'

    id = Column(INTEGER(11), primary_key=True)
    profiling_task_result_id = Column(INTEGER(11))
    start_state = Column(INTEGER(11))
    state_order = Column(INTEGER(11))
    consume_time = Column(BIGINT(20))
    is_pressure_test = Column(TINYINT(4), server_default=text("1"))


class QuartzBean(Base):
    __tablename__ = 'quartz_bean'
    __table_args__ = {'comment': '定时任务'}

    id = Column(INTEGER(11), primary_key=True, comment='任务id')
    job_id = Column(String(50))
    job_Des = Column(String(50), comment=' 任务名称')
    job_class = Column(String(50), comment='任务执行类')
    status = Column(INTEGER(11), comment='任务状态 测试环境全部改成0')
    cron_expression = Column(String(50), comment='任务运行时间表达式')
    server_ip = Column(String(20))
    receivers = Column(String(200))


class SysDict(Base):
    __tablename__ = 'sys_dict'
    __table_args__ = {'comment': '字典表'}

    id = Column(BIGINT(20), primary_key=True)
    type_code = Column(String(50), nullable=False, comment='字典类型编码（例如：gender, user_status）')
    type_name = Column(String(100), nullable=False, comment='字典类型名称（例如：性别、用户状态）')
    value = Column(LONGTEXT, nullable=False, comment='字典值（例如：男、女）')
    label = Column(String(255), nullable=False, comment='显示标签')
    sort = Column(INTEGER(11), server_default=text("0"), comment='排序')
    create_time = Column(DateTime, server_default=text("current_timestamp()"))
    update_time = Column(DateTime, server_default=text("current_timestamp() ON UPDATE current_timestamp()"))
    is_del = Column(TINYINT(4), server_default=text("0"), comment='是否删除')


class SysTaskCompile(Base):
    __tablename__ = 'sys_task_compile'

    task_id = Column(String(64), primary_key=True, comment='任务ID')
    task_compile_info = Column(LONGTEXT, comment='任务编译信息')
    task_without_compensate_prog = Column(LONGTEXT, comment='串扰补偿前的量子程序')
    convertQProg = Column(LONGTEXT)
    mappingQProg = Column(LONGTEXT)
    mappingQubit = Column(String(5000), nullable=False, server_default=text("'\"\"'"))


class SysUser(Base):
    __tablename__ = 'sys_user'

    id = Column(BIGINT(20), primary_key=True)
    username = Column(String(255), nullable=False)
    password = Column(CHAR(64), nullable=False)
    status = Column(TINYINT(4), nullable=False)
    role_ids = Column(TINYINT(4), nullable=False)
    vip = Column(TINYINT(4), nullable=False, server_default=text("1"))
    api_key = Column(String(64))
    realname = Column(String(255))
    company = Column(String(255))
    salt = Column(String(16))
    mark = Column(TINYINT(4), nullable=False, server_default=text("1"))
    first_name = Column(String(100), nullable=False, comment='名')
    last_name = Column(String(100), nullable=False, comment='姓')
    email = Column(String(255))
    phone_number = Column(String(50), nullable=False, comment='手机号')
    passport_number = Column(String(50), comment='护照号')
    national_id = Column(String(50), comment='身份证号')
    institution = Column(String(255), nullable=False, comment='所属机构')


class SysUserTask(Base):
    __tablename__ = 'sys_user_task'

    id = Column(BIGINT(20), primary_key=True, comment='主键ID')
    taskid = Column(VARCHAR(64), nullable=False, unique=True, comment='任务ID')
    userid = Column(BIGINT(20), nullable=False, comment='用户ID')
    task_discribe = Column(LONGTEXT, comment='任务描述')


class TaskInfo(Base):
    __tablename__ = 'task_info'

    task_id = Column(String(64), primary_key=True)
    cloud_user_for_pqc = Column(INTEGER(11))


class TaskStatu(Base):
    __tablename__ = 'task_status'

    taskId = Column(String(64), primary_key=True, comment='taskId')
    taskState = Column(INTEGER(11), nullable=False, server_default=text("0"), comment='taskState')
    qProg = Column(LONGTEXT, nullable=False, comment='qProg')
    qProgLength = Column(INTEGER(11), nullable=False, server_default=text("0"), comment='qProgLength')
    qmType = Column(INTEGER(11), nullable=False, server_default=text("0"), comment='qmType')
    backendType = Column(String(255), comment='backendType')
    taskType = Column(INTEGER(11), nullable=False, server_default=text("0"), comment='taskType')
    priority = Column(INTEGER(11), server_default=text("0"))
    configuration = Column(LONGTEXT)
    convertQProg = Column(LONGTEXT, comment='convertQProg')
    mappingQProg = Column(LONGTEXT, comment='mappingQProg')
    mappingQubit = Column(String(1024), nullable=False, server_default=text("''"), comment='mappingQubit')
    requiredCore = Column(INTEGER(11), nullable=False, server_default=text("0"), comment='requiredCore')
    taskResult = Column(LONGTEXT, comment='taskResult')
    probCount = Column(LONGTEXT, comment='probCount')
    qSTResult = Column(LONGTEXT, comment='qSTResult')
    qSTFidelity = Column(LONGTEXT, comment='qSTFidelity')
    timeStr = Column(LONGTEXT, comment='timeStr')
    startTime = Column(BIGINT(20), comment='startTime')
    endTime = Column(BIGINT(20), comment='endTime')
    timeStamp = Column(String(1024), server_default=text("''"))
    errCode = Column(INTEGER(11), nullable=False, server_default=text("0"), comment='errCode')
    errInfo = Column(LONGTEXT, comment='errInfo')
    callbackAddr = Column(String(256), server_default=text("''"), comment='callbackAddr')


class TestBinaryDatum(Base):
    __tablename__ = 'test_binary_data'

    id = Column(INTEGER(11), primary_key=True)
    binary_data = Column(LONGBLOB)


class XebPartTask(Base):
    __tablename__ = 'xeb_part_task'
    __table_args__ = {'comment': 'XEB局部任务'}

    id = Column(BIGINT(20), primary_key=True, comment='主键ID')
    task_id = Column(String(64), nullable=False, unique=True, comment='任务ID')
    chip_id = Column(String(64), nullable=False, comment='芯片ID')
    test_depth = Column(String(255), nullable=False, comment='测试深度')
    test_bit = Column(String(255), nullable=False, comment='测试比特')
    cron_expression = Column(String(255), nullable=False, comment='执行表达式')
    enabled = Column(TINYINT(4), server_default=text("0"), comment='开启: 0-未开启, 1-已开启')
    error_info = Column(LONGTEXT, comment='异常信息')
    start_time = Column(DateTime, comment='开始时间')
    end_time = Column(DateTime, comment='结束时间')
    is_deleted = Column(TINYINT(4), server_default=text("0"), comment='是否删除: 0-未删除, 1-已删除')


class XebPartTaskDetail(Base):
    __tablename__ = 'xeb_part_task_detail'
    __table_args__ = {'comment': 'XEB局部任务详情'}

    id = Column(BIGINT(20), primary_key=True, comment='主键ID')
    xeb_part_task_id = Column(BIGINT(20), nullable=False, comment='XEB局部任务ID')
    status = Column(TINYINT(4), comment='状态：1.已提交；2.异常；3.已完成；4.已取消')
    fidelity = Column(Float(asdecimal=True), comment='结果')
    error_info = Column(LONGTEXT, comment='异常信息')
    start_time = Column(DateTime, comment='开始时间')
    end_time = Column(DateTime, comment='结束时间')
    is_deleted = Column(TINYINT(4), server_default=text("0"), comment='是否删除: 0-未删除, 1-已删除')


class XebTest(Base):
    __tablename__ = 'xeb_test'
    __table_args__ = {'comment': 'XEBs测试表'}

    id = Column(BIGINT(20), primary_key=True, comment='主键ID')
    result = Column(LONGTEXT, comment='结果')
    status = Column(BIGINT(20), comment='状态：1.已提交；2.异常；3.已完成')
    error_info = Column(LONGTEXT, comment='异常信息')
    start_time = Column(DateTime, comment='开始时间')
    end_time = Column(DateTime, comment='结束时间')
    pic_path = Column(LONGTEXT, comment='图片地址')
    total_pic_path = Column(String(255), comment='总图地址')
    task_id = Column(String(255), comment='算法推送的任务ID')
    single_result = Column(LONGTEXT, comment='单门结果')
    single_pic_path = Column(LONGTEXT, comment='单门图片地址')
    is_deleted = Column(TINYINT(4), server_default=text("0"), comment='是否删除: 0-未删除, 1-已删除')
    progress = Column(INTEGER(11), server_default=text("0"), comment='进度')
    chip_id = Column(String(64), comment='芯片ID')
    label = Column(TINYINT(4), comment='工作标签')
