/**
 * TradingView Lightweight Charts 客户端交互脚本
 * 处理图表渲染、十字线、价格显示和交易标记
 */

if (!window.dash_clientside) {
    window.dash_clientside = {};
}

// 辅助函数 - 数字补零
const pad = (n) => n < 10 ? '0' + n : n;

// 修正时间戳函数，处理可能的时区或时间偏移问题
const correctTimestamp = (timestamp) => {
    // 如果传入的是秒为单位的时间戳，转换为毫秒
    if (timestamp < 10000000000) {
        timestamp = timestamp * 1000;
    }
    
    // 这里不再添加16小时的修正，直接返回正确的时间戳
    return timestamp;
};

// 格式化日期时间，转换为正确的时间
const formatBeijingTime = (timestamp) => {
    // 修正时间戳
    const correctedTimestamp = correctTimestamp(timestamp);
    
    // 创建日期对象
    const date = new Date(correctedTimestamp);
    
    // 调整时间：减去10个小时
    const adjustedDate = new Date(date.getTime());
    
    // 格式化日期和时间
    const formattedDate = `${adjustedDate.getFullYear()}-${pad(adjustedDate.getMonth() + 1)}-${pad(adjustedDate.getDate())}`;
    const formattedTime = `${pad(adjustedDate.getHours())}:${pad(adjustedDate.getMinutes())}`;
    
    return { 
        date: formattedDate, 
        time: formattedTime, 
        full: `${formattedDate} ${formattedTime}`
    };
};

// 创建图表图例
const createLegend = (chart, container, items) => {
    const legendContainer = document.createElement('div');
    legendContainer.classList.add('chart-legend');
    Object.assign(legendContainer.style, {
        position: 'absolute',
        left: '12px',
        top: '12px',
        zIndex: 2,
        fontSize: '12px',
        lineHeight: '14px',
        fontFamily: 'sans-serif',
        padding: '8px',
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        color: 'white',
        borderRadius: '4px',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px'
    });
    
    if (!items || items.length === 0) {
        return null;
    }
    
    items.forEach(item => {
        const itemRow = document.createElement('div');
        itemRow.style.display = 'flex';
        itemRow.style.alignItems = 'center';
        itemRow.style.marginBottom = '2px';
        
        const colorBox = document.createElement('div');
        colorBox.style.width = '8px';
        colorBox.style.height = '8px';
        colorBox.style.backgroundColor = item.color;
        colorBox.style.marginRight = '6px';
        
        const label = document.createElement('span');
        label.textContent = item.text;
        
        itemRow.appendChild(colorBox);
        itemRow.appendChild(label);
        legendContainer.appendChild(itemRow);
    });
    
    container.appendChild(legendContainer);
    return legendContainer;
};

// 添加自定义的鼠标交互处理
const addChartInteractions = (chartInstance, containerElement, isMainChart = false) => {
    // 鼠标滚轮事件 - 缩放图表
    containerElement.addEventListener('wheel', (e) => {
        e.preventDefault(); // 阻止页面滚动
        
        // 获取鼠标位置相对于容器的坐标
        const rect = containerElement.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        
        // 检查鼠标是否在价格轴上 (假设价格轴在左侧，宽度约为50px)
        const isPriceAxisArea = mouseX < 50;
        
        if (isPriceAxisArea) {
            // 鼠标在价格轴上，控制价格缩放
            // 对于4.0.1版本，我们依赖图表库的内置行为，这里不需要显式调用缩放API
            // 确保 chartOptions 中的 handleScale.axisPressedMouseMove.price 和 handleScale.mouseWheel 设置为 true
                } else {
            // 鼠标在图表主体上，控制时间轴缩放（默认行为）
            // chartInstance.timeScale().scrollPosition(chartInstance.timeScale().scrollPosition() - e.deltaY / 100);
        }
    }, { passive: false });

    // 添加双击重置功能
    containerElement.addEventListener('dblclick', (e) => {
        const rect = containerElement.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        
        if (mouseX < 50) {
            // 双击价格轴，重置价格范围
            const priceScale = chartInstance.priceScale('left');
            if (priceScale) {
                priceScale.applyOptions({
                    autoScale: true
                });
                // 自动缩放后恢复手动模式
                setTimeout(() => {
                    priceScale.applyOptions({
                        autoScale: false // 或者根据需要保持true
                    });
                }, 10);
            }
        } else {
            // 双击图表主体，重置时间范围
            chartInstance.timeScale().fitContent();
        }
    });
    
    // 创建时间标签元素
    const timeLabel = document.createElement('div');
    timeLabel.className = 'time-label';
    Object.assign(timeLabel.style, {
        position: 'absolute',
        bottom: '25px',
        left: '50%',
        transform: 'translateX(-50%)',
        backgroundColor: 'rgba(33, 56, 77, 0.8)',
        color: 'white',
        padding: '2px 6px',
        borderRadius: '3px',
        fontSize: '12px',
        fontFamily: 'sans-serif',
        pointerEvents: 'none',
        zIndex: 5,
        opacity: 0,
        transition: 'opacity 0.2s ease'
    });
    containerElement.appendChild(timeLabel);
    
    // 订阅十字线移动事件
    chartInstance.subscribeCrosshairMove((param) => {
        if (param && param.time) {
            // 使用新的格式化函数处理时间
            const timeInfo = formatBeijingTime(param.time);
            
            // 更新标签内容
            timeLabel.textContent = `${timeInfo.full}`;
            timeLabel.style.opacity = '1';
            
            // 获取鼠标位置
            if (param.point) {
                // 将标签放在十字线下方
                timeLabel.style.left = `${param.point.x}px`;
                timeLabel.style.transform = 'translateX(-50%)';
            }
        } else {
            // 鼠标离开图表区域，隐藏标签
            timeLabel.style.opacity = '0';
        }
    });
};

// 在这里添加全局样式
const addGlobalStyles = () => {
    const style = document.createElement('style');
    style.textContent = `
        .dragging * {
            transition: none !important;
            will-change: transform;
            pointer-events: none;
        }
        
        .fullscreen-button:hover {
            background-color: rgba(33, 56, 77, 0.9) !important;
        }
        
        /* 全屏模式下的特殊样式 */
        :fullscreen {
            background-color: #151924;
            padding: 20px;
        }

        /* 增加图表容器的样式，提高渲染性能 */
        .chart-container {
            will-change: transform;
            transform: translateZ(0);
            backface-visibility: hidden;
        }
        
        /* 拖拽性能优化 */
        .drag-performance {
            will-change: height;
            transition: none !important;
        }
        
        /* 提高图表渲染性能 */
        .tv-lightweight-charts {
            contain: strict;
            will-change: transform;
        }
        
        /* 鼠标拖拽超出图表区域时禁用文本选择 */
        body.dragging {
            user-select: none;
            -webkit-user-select: none;
        }
        
        /* 图表调整大小时的平滑过渡 */
        .tv-lightweight-charts canvas {
            transition: height 0.1s ease-out;
        }
        
        /* 图表调整大小时禁用过渡效果以提高性能 */
        body.charts-resizing .tv-lightweight-charts canvas,
        body.active-chart-zooming .tv-lightweight-charts canvas {
            transition: none !important;
        }
        
        /* 提高指标线条的平滑度 */
        .tv-lightweight-charts path {
            shape-rendering: geometricPrecision;
        }
        
        /* 活动缩放期间优化性能 */
        body.active-chart-zooming * {
            pointer-events: auto !important;
            will-change: transform;
        }
        
        /* 添加交易标记提示样式 */
        #trade-tooltip {
            position: absolute;
            background-color: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 8px;
            border-radius: 4px;
            font-size: 12px;
            z-index: 1000;
            pointer-events: none;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        }
        
        /* 时间标签样式 */
        .time-label {
            box-shadow: 0 1px 3px rgba(0,0,0,0.3);
            white-space: nowrap;
        }
        
        /* 高亮标记样式 - 增强版 */
        .highlighted-marker {
            filter: drop-shadow(0 0 8px rgba(255, 215, 0, 0.9)) !important;
            transform: scale(1.4) !important;
            transition: all 0.3s ease !important;
            z-index: 9999 !important;
        }
        
        .highlighted-marker text {
            font-weight: bold !important;
            fill: #FFEB3B !important;
            stroke: #000000 !important;
            stroke-width: 0.3px !important;
            text-shadow: 0px 0px 4px rgba(0, 0, 0, 0.9) !important;
        }
        
        .highlighted-marker path {
            stroke: #FFD700 !important;
            stroke-width: 3px !important;
            fill: #FFC107 !important;
        }
        
        /* 添加一个脉冲动画效果 */
        @keyframes markerPulse {
            0% { transform: scale(1.3); filter: drop-shadow(0 0 5px rgba(255, 215, 0, 0.8)); }
            50% { transform: scale(1.5); filter: drop-shadow(0 0 12px rgba(255, 215, 0, 1)); }
            100% { transform: scale(1.3); filter: drop-shadow(0 0 5px rgba(255, 215, 0, 0.8)); }
        }
        
        /* 应用脉冲动画 */
        .highlighted-marker {
            animation: markerPulse 1.5s infinite ease-in-out !important;
        }
        
        /* 为导航面板添加闪烁动画，当显示仓位信息时 */
        @keyframes panelHighlight {
            0% { box-shadow: 0 0 5px rgba(255, 215, 0, 0.3); }
            50% { box-shadow: 0 0 15px rgba(255, 215, 0, 0.7); }
            100% { box-shadow: 0 0 5px rgba(255, 215, 0, 0.3); }
        }
        
        /* 为SVG元素添加通用选择器 */
        .tv-lightweight-charts g[data-marker-id],
        .tv-lightweight-charts text[data-marker-id],
        .tv-lightweight-charts *[data-marker-id] {
            cursor: pointer !important;
            transition: transform 0.2s ease, filter 0.2s ease !important;
        }
        
        .tv-lightweight-charts g[data-marker-id]:hover,
        .tv-lightweight-charts text[data-marker-id]:hover,
        .tv-lightweight-charts *[data-marker-id]:hover {
            transform: scale(1.2) !important;
            filter: drop-shadow(0 0 4px rgba(255, 215, 0, 0.6)) !important;
        }
        
        /* 确保导航面板在有内容时总是可见 */
        #navigation-controller:not(:empty) {
            display: block !important;
            opacity: 1 !important;
            animation: panelHighlight 2s infinite ease-in-out;
        }
        
        /* 加载更多按钮动画 */
        @keyframes pulse {
            0% { transform: translateY(-50%) scale(1); }
            50% { transform: translateY(-50%) scale(1.05); }
            100% { transform: translateY(-50%) scale(1); }
        }
        
        .load-more-button {
            animation: pulse 2s infinite ease-in-out;
            user-select: none;
        }
        
        .load-more-button:active {
            transform: translateY(-48%) scale(0.97);
        }
    `;
    document.head.appendChild(style);
};

// 创建全屏按钮函数
const createFullscreenButton = (container) => {
    // 检查是否已经有全屏按钮
    if (container.querySelector('.fullscreen-button')) {
        return container.querySelector('.fullscreen-button');
    }
    
    // 创建全屏按钮
    const fullscreenBtn = document.createElement('div');
    fullscreenBtn.className = 'fullscreen-button';
    fullscreenBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z" fill="currentColor"/></svg>';
    
    // 设置按钮样式
    Object.assign(fullscreenBtn.style, {
        position: 'absolute',
        right: '10px',
        top: '10px',
        width: '28px',
        height: '28px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'rgba(33, 56, 77, 0.6)',
        color: 'white',
        borderRadius: '4px',
        cursor: 'pointer',
        zIndex: 10,
        transition: 'background-color 0.2s ease',
    });
    
    // 添加全屏切换功能
    fullscreenBtn.addEventListener('click', () => {
        if (!document.fullscreenElement) {
            // 进入全屏
            if (container.requestFullscreen) {
                container.requestFullscreen();
            } else if (container.webkitRequestFullscreen) {
                container.webkitRequestFullscreen();
            } else if (container.msRequestFullscreen) {
                container.msRequestFullscreen();
            }
        } else {
            // 退出全屏
            if (document.exitFullscreen) {
                document.exitFullscreen();
            } else if (document.webkitExitFullscreen) {
                document.webkitExitFullscreen();
            } else if (document.msExitFullscreen) {
                document.msExitFullscreen();
            }
        }
    });
    
    // 添加到容器
    container.appendChild(fullscreenBtn);
    return fullscreenBtn;
};

// 创建"加载更多"按钮函数
const createLoadMoreButton = (container, chart) => {
    // 检查是否已经有加载更多按钮
    if (container.querySelector('.load-more-button')) {
        return container.querySelector('.load-more-button');
    }
    
    // 创建加载更多按钮
    const loadMoreBtn = document.createElement('div');
    loadMoreBtn.className = 'load-more-button';
    loadMoreBtn.innerText = '加载更多';
    
    // 设置按钮样式
    Object.assign(loadMoreBtn.style, {
        position: 'absolute',
        right: '20px',
        top: '50%',
        transform: 'translateY(-50%)',
        padding: '10px 15px',
        backgroundColor: 'rgba(33, 150, 243, 0.9)',
        color: 'white',
        borderRadius: '6px',
        cursor: 'pointer',
        zIndex: 100,
        transition: 'all 0.3s ease',
        opacity: '0',
        pointerEvents: 'none',
        fontFamily: 'sans-serif',
        fontSize: '14px',
        fontWeight: 'bold',
        boxShadow: '0 4px 8px rgba(0,0,0,0.3)',
        border: '1px solid rgba(255,255,255,0.2)'
    });

    // 添加悬停效果
    loadMoreBtn.addEventListener('mouseover', () => {
        loadMoreBtn.style.backgroundColor = 'rgba(33, 150, 243, 1)';
        loadMoreBtn.style.boxShadow = '0 6px 12px rgba(0,0,0,0.4)';
        loadMoreBtn.style.transform = 'translateY(-52%)';
    });
    
    loadMoreBtn.addEventListener('mouseout', () => {
        loadMoreBtn.style.backgroundColor = 'rgba(33, 150, 243, 0.9)';
        loadMoreBtn.style.boxShadow = '0 4px 8px rgba(0,0,0,0.3)';
        loadMoreBtn.style.transform = 'translateY(-50%)';
    });
    
    // 添加加载更多功能
    loadMoreBtn.addEventListener('click', () => {
        loadMoreBtn.innerText = '加载中...';
        loadMoreBtn.style.backgroundColor = 'rgba(150, 150, 150, 0.8)';
        loadMoreBtn.style.cursor = 'wait';
        
        console.log('加载更多按钮被点击');
        
        try {
            // 优先使用辅助按钮触发，这是更可靠的方法
            let helperButton = document.getElementById('load-more-helper-button');
            if (!helperButton) {
                helperButton = document.createElement('button');
                helperButton.id = 'load-more-helper-button';
                helperButton.style.display = 'none';
                document.body.appendChild(helperButton);
                console.log('创建了新的load-more-helper-button元素');
            }
            
            // 创建或获取隐藏的加载更多触发器 - 作为备用方案
            let loadMoreTrigger = document.getElementById('load-more-trigger');
            if (!loadMoreTrigger) {
                loadMoreTrigger = document.createElement('input');
                loadMoreTrigger.id = 'load-more-trigger';
                loadMoreTrigger.type = 'hidden';
                loadMoreTrigger.value = '0';
                document.body.appendChild(loadMoreTrigger);
                console.log('创建了新的load-more-trigger元素');
            }
            
            // 更新触发器值
            const newValue = parseInt(loadMoreTrigger.value || '0') + 1;
            loadMoreTrigger.value = newValue;
            console.log(`更新load-more-trigger值为: ${newValue}`);
            
            // 触发change事件
            const event = new Event('change', { bubbles: true, cancelable: true });
            loadMoreTrigger.dispatchEvent(event);
            console.log('触发了load-more-trigger的change事件');
            
            // 触发辅助按钮点击事件 - 这是主要方法
            helperButton.click();
            console.log('触发了辅助按钮点击事件');
            
            // 添加超时处理，如果20秒内没有响应则恢复按钮状态
            setTimeout(() => {
                if (loadMoreBtn.innerText === '加载中...') {
                    loadMoreBtn.innerText = '加载更多';
                    loadMoreBtn.style.backgroundColor = 'rgba(33, 150, 243, 0.9)';
                    loadMoreBtn.style.cursor = 'pointer';
                    console.log('加载超时，已恢复按钮状态');
                }
            }, 20000);
        } catch (e) {
            console.error('触发加载更多事件失败:', e);
            
            // 恢复按钮状态
            loadMoreBtn.innerText = '加载更多';
            loadMoreBtn.style.backgroundColor = 'rgba(33, 150, 243, 0.9)';
            loadMoreBtn.style.cursor = 'pointer';
        }
    });
    
    // 添加到容器
    container.appendChild(loadMoreBtn);
    return loadMoreBtn;
};

// 检测图表滚动到最右侧并显示加载更多按钮
const setupLoadMoreDetection = (chart, container) => {
    const loadMoreBtn = createLoadMoreButton(container, chart);
    
    // 检测图表滚动位置
    const checkRightEdge = () => {
        try {
            if (!chart || !chartData || !chartData.candlestick) {
                // console.log("图表或数据尚未准备好，不显示加载更多按钮");
                return;
            }
            
            const timeScale = chart.timeScale();
            const logicalRange = timeScale.getVisibleLogicalRange();
            const barCount = chartData.candlestick.length;
            
            if (!logicalRange) {
                // console.log("无法获取可见范围，不显示加载更多按钮");
                return;
            }
            
            // 记录日志 - 删除此日志以避免频繁打印
            // console.log(`当前K线总数: ${barCount}, 可见范围: ${logicalRange.from.toFixed(2)} - ${logicalRange.to.toFixed(2)}`);
            
            // 如果可见范围接近右边缘（最后30个K线），显示按钮
            // 增加显示按钮的触发条件，使其更容易被激活
            const isNearRightEdge = (barCount - logicalRange.to) < 30;
            const isNearEnd = (logicalRange.to / barCount) > 0.8; // 当查看的是后20%的数据时
            
            if (isNearRightEdge || isNearEnd) {
                // console.log("图表接近右侧边缘，显示加载更多按钮");
                loadMoreBtn.style.opacity = '1';
                loadMoreBtn.style.pointerEvents = 'auto';
                
                // 添加脉动动画效果
                loadMoreBtn.style.animation = 'pulseButton 2s infinite';
                // 添加CSS动画
                if (!document.getElementById('pulse-animation')) {
                    const style = document.createElement('style');
                    style.id = 'pulse-animation';
                    style.textContent = `
                        @keyframes pulseButton {
                            0% { transform: translateY(-50%) scale(1); }
                            50% { transform: translateY(-50%) scale(1.05); }
                            100% { transform: translateY(-50%) scale(1); }
                        }
                    `;
                    document.head.appendChild(style);
                }
            } else {
                loadMoreBtn.style.opacity = '0';
                loadMoreBtn.style.pointerEvents = 'none';
                loadMoreBtn.style.animation = 'none';
            }
        } catch (e) {
            console.error('检查右边缘时出错:', e);
        }
    };
    
    // 监听图表滚动事件
    chart.timeScale().subscribeVisibleLogicalRangeChange(checkRightEdge);
    
    // 定期检查位置（以防止某些情况下事件未触发）
    const intervalId = setInterval(checkRightEdge, 1000);
    
    // 返回卸载函数
    return {
        unsubscribe: () => {
            clearInterval(intervalId);
            const handler = chart.timeScale().subscribeVisibleLogicalRangeChange(checkRightEdge);
            if (handler && typeof handler.unsubscribe === 'function') {
                handler.unsubscribe();
            }
        }
    };
};

// 初始化客户端命名空间
window.dash_clientside.clientside = {
    /**
     * 初始化图表
     * @param {Object} chartData - 图表数据
     * @param {Array} tradesData - 交易数据
     * @param {boolean} showEma - 是否显示EMA
     * @param {boolean} showTrades - 是否显示交易标记
     * @param {boolean} showBollinger - 是否显示布林带
     * @param {boolean} showRsi - 是否显示RSI
     * @param {boolean} showMacd - 是否显示MACD
     * @param {string} containerId - 容器ID
     * @returns {null} - 无返回值
     */
    initializeChart: function(chartData, tradesData, showEma, showTrades, showBollinger, showRsi, showMacd, containerId) {
        // 检查LightweightCharts是否已定义
        if (typeof LightweightCharts === 'undefined') {
            console.error('LightweightCharts库未加载，尝试动态加载...');
            
            // 创建一个消息元素
            const container = document.getElementById(containerId);
            if (container) {
                container.innerHTML = '<div class="text-center p-5">正在加载图表库，请稍候...</div>';
                
                // 动态加载库
                const script = document.createElement('script');
                script.src = 'https://unpkg.com/lightweight-charts@4.0.1/dist/lightweight-charts.standalone.production.js';
                script.onload = () => {
                    console.log('库加载成功，重新初始化图表...');
                    setTimeout(() => this.initializeChart(chartData, tradesData, showEma, showTrades, showBollinger, showRsi, showMacd, containerId), 500);
                };
                script.onerror = () => {
                    console.error('库加载失败');
                    if (container) {
                        container.innerHTML = '<div class="text-center p-5 text-danger">图表库加载失败，请刷新页面重试</div>';
                    }
                };
                document.head.appendChild(script);
            }
            return null;
        }
        
        // 如果没有数据，不渲染图表
        if (!chartData) return null;
        
        // 解析数据
        try {
            chartData = JSON.parse(chartData);
            tradesData = tradesData ? JSON.parse(tradesData) : [];
        } catch (e) {
            console.error('解析图表数据失败:', e);
            return null;
        }
        
        // 获取容器元素
        const container = document.getElementById(containerId);
        if (!container) return null;
        
        // 清空容器
        container.innerHTML = '';
        
        // 如果数据为空，显示提示信息
        if (!chartData.candlestick || chartData.candlestick.length === 0) {
            container.innerHTML = '<div class="text-center p-5">没有可用的数据</div>';
            return null;
        }
        
        // 创建主要容器结构
        const chartContainer = document.createElement('div');
        chartContainer.style.width = '100%';
        chartContainer.style.height = 'calc(70% - 5px)';
        chartContainer.style.position = 'relative';
        
        const volumeContainer = document.createElement('div');
        volumeContainer.style.width = '100%';
        volumeContainer.style.height = 'calc(30% - 5px)';
        volumeContainer.style.position = 'relative';
        volumeContainer.style.marginTop = '-25px';
        
        // 创建分隔线，可拖动
        const dividerContainer = document.createElement('div');
        // dividerContainer.style.width = '100%';
        // dividerContainer.style.height = '10px';
        // dividerContainer.style.position = 'relative';
        // dividerContainer.style.cursor = 'ns-resize';
        // dividerContainer.style.marginTop = '5px';
        // dividerContainer.style.marginBottom = '5px';
        
        const divider = document.createElement('div');
        // divider.style.width = '100%';
        // divider.style.height = '1px';
        // divider.style.background = '#758696';
        // divider.style.borderStyle = 'dashed';
        // divider.style.position = 'absolute';
        // divider.style.top = '50%';
        // divider.style.transform = 'translateY(-50%)';
        dividerContainer.appendChild(divider);
        
        // 显示比例的标签
        const ratioLabel = document.createElement('div');
        ratioLabel.style.position = 'absolute';
        ratioLabel.style.right = '10px';
        ratioLabel.style.top = '50%';
        ratioLabel.style.transform = 'translateY(-50%)';
        ratioLabel.style.color = '#758696';
        ratioLabel.style.fontSize = '12px';
        ratioLabel.style.background = 'rgba(33, 56, 77, 0.6)';
        ratioLabel.style.padding = '2px 5px';
        ratioLabel.style.borderRadius = '3px';
        ratioLabel.textContent = '70/30';
        dividerContainer.appendChild(ratioLabel);
        
        // 添加容器到主容器
        container.appendChild(chartContainer);
        container.appendChild(dividerContainer);
        container.appendChild(volumeContainer);
        
        // 为RSI和MACD创建额外的容器（如果需要）
        let rsiContainer = null;
        let macdContainer = null;
        
        if (showRsi) {
            rsiContainer = document.createElement('div');
            rsiContainer.style.width = '100%';
            rsiContainer.style.height = '250px';  // 增加高度到250px
            rsiContainer.style.position = 'relative';
            rsiContainer.style.marginTop = '-20px';  // 减少与前一个元素的间距
            
            // 添加RSI容器到主容器
            container.appendChild(rsiContainer);
        }
        
        if (showMacd) {
            macdContainer = document.createElement('div');
            macdContainer.style.width = '100%';
            macdContainer.style.height = '250px';  // 增加高度到250px
            macdContainer.style.position = 'relative';
            rsiContainer ? macdContainer.style.marginTop = '-20px' : macdContainer.style.marginTop = '-20px';  // 根据是否有RSI容器调整间距
            
            // 添加MACD容器到主容器
            container.appendChild(macdContainer);
        }
        
        // 默认的高度比例
        let chartRatio = 0.7;
        
        // 分隔线拖动逻辑
        let isDragging = false;
        let startY = 0;
        let initialChartHeight = 0;
        let containerHeight = 0;
        let rafDragId = null; // 添加requestAnimationFrame ID变量
        
        dividerContainer.addEventListener('mousedown', function(e) {
            isDragging = true;
            startY = e.clientY;
            initialChartHeight = chartContainer.offsetHeight;
            
            // 根据当前容器中是否有RSI或MACD计算容器高度
            let rsiHeight = 0;
            let macdHeight = 0;
            
            // 安全地检查rsiChart和rsiContainer是否存在
            if (rsiChart && typeof rsiContainer !== 'undefined') {
                rsiHeight = rsiContainer.offsetHeight;
            }
            
            // 安全地检查macdChart和macdContainer是否存在
            if (macdChart && typeof macdContainer !== 'undefined') {
                macdHeight = macdContainer.offsetHeight;
            }
            
            // 累加除分隔线外的所有指标高度
            containerHeight = container.offsetHeight - dividerContainer.offsetHeight - rsiHeight - macdHeight;
            
            document.body.style.cursor = 'ns-resize';
            e.preventDefault();
            
            // 添加一个类以减少重绘，提高性能
            container.classList.add('dragging');
            
            // 添加性能相关的CSS类
            chartContainer.classList.add('drag-performance');
            volumeContainer.classList.add('drag-performance');
            
            // 安全地检查rsiChart和rsiContainer是否存在
            if (rsiChart && typeof rsiContainer !== 'undefined') {
                rsiContainer.classList.add('drag-performance');
            }
            
            // 安全地检查macdChart和macdContainer是否存在
            if (macdChart && typeof macdContainer !== 'undefined') {
                macdContainer.classList.add('drag-performance');
            }
        });
        
        document.addEventListener('mousemove', function(e) {
            if (!isDragging) return;
            
            // 取消之前的动画帧请求
            if (rafDragId) {
                cancelAnimationFrame(rafDragId);
            }
            
            // 使用requestAnimationFrame来优化拖拽性能，减少不必要的渲染
            rafDragId = requestAnimationFrame(() => {
                const delta = e.clientY - startY;
                const newChartHeight = Math.max(50, Math.min(containerHeight - 50, initialChartHeight + delta));
                
                chartRatio = newChartHeight / containerHeight;
                const volumeRatio = 1 - chartRatio;
                
                // 更新价格和成交量图表的高度
                chartContainer.style.height = `calc(${Math.round(chartRatio * 100)}% - 5px)`;
                volumeContainer.style.height = `calc(${Math.round(volumeRatio * 100)}% - 5px)`;
                
                // 更新比例标签
                ratioLabel.textContent = `${Math.round(chartRatio * 100)}/${Math.round(volumeRatio * 100)}`;
                
                // 不要在拖拽过程中调整图表大小，只在拖拽结束后进行
                // resizeAllCharts();
            });
                
                e.preventDefault();
        });
        
        document.addEventListener('mouseup', function() {
            if (!isDragging) return;
            
            // 拖拽完成，取消所有挂起的动画帧请求
            if (rafDragId) {
                cancelAnimationFrame(rafDragId);
                rafDragId = null;
            }
            
                isDragging = false;
                document.body.style.cursor = '';
            container.classList.remove('dragging');
            
            // 移除性能相关的CSS类
            chartContainer.classList.remove('drag-performance');
            volumeContainer.classList.remove('drag-performance');
            
            // 安全地检查rsiChart和rsiContainer是否存在
            if (rsiChart && typeof rsiContainer !== 'undefined') {
                rsiContainer.classList.remove('drag-performance');
            }
            
            // 安全地检查macdChart和macdContainer是否存在
            if (macdChart && typeof macdContainer !== 'undefined') {
                macdContainer.classList.remove('drag-performance');
            }
            
            // 拖拽完成后，不仅要调整大小，还需要重新同步一次所有图表的可见范围
            // 使用更短的延迟并直接执行所有操作
            setTimeout(() => {
                // 先调整图表大小
                resizeAllCharts();
                
                // 然后同步时间轴
                setTimeout(() => {
                    const timeRange = priceChart.timeScale().getVisibleRange();
                    if (timeRange) {
                        allCharts.forEach(chart => {
                            if (chart !== priceChart) {
                                chart.timeScale().setVisibleRange(timeRange);
                            }
                        });
                    }
                }, 50);
            }, 50);
        });
        
        // 通用图表配置
        const commonChartOptions = {
            layout: {
                background: { color: '#151924' },
                textColor: '#d1d4dc',
                fontSize: 12,
                fontFamily: 'Roboto, sans-serif',
            },
            grid: {
                vertLines: { color: '#2B2B43', style: LightweightCharts.LineStyle.Dotted },
                horzLines: { color: '#2B2B43', style: LightweightCharts.LineStyle.Dotted },
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
                vertLine: {
                    width: 1,
                    color: '#758696',
                    style: LightweightCharts.LineStyle.Dashed,
                    labelBackgroundColor: '#758696',
                },
                horzLine: {
                    width: 1,
                    color: '#758696',
                    style: LightweightCharts.LineStyle.Dashed,
                    labelBackgroundColor: '#758696',
                },
            },
            timeScale: {
                borderColor: '#2B2B43',
                timeVisible: true,
                secondsVisible: false,
                tickMarkFormatter: (time, tickMarkType, locale) => {
                    // 使用修正的时间戳
                    const timestamp = correctTimestamp(time);
                    const date = new Date(timestamp);
                    
                    // 调整时间：减去10个小时
                    const adjustedDate = new Date(date.getTime() - 10 * 60 * 60 * 1000);
                    
                    // 使用调整后的时间来决定格式
                    switch (tickMarkType) {
                        case LightweightCharts.TickMarkType.Year:
                            return adjustedDate.getFullYear().toString();
                        case LightweightCharts.TickMarkType.Month:
                            // 使用Intl API来获取本地化的月份名称缩写
                            return new Intl.DateTimeFormat(locale, { month: 'short' }).format(adjustedDate);
                        case LightweightCharts.TickMarkType.Day:
                            return pad(adjustedDate.getDate());
                        case LightweightCharts.TickMarkType.Hour:
                            // 每4小时标记一个小时文本，其他小时留空或显示更简略标记
                            if (adjustedDate.getHours() % 4 === 0) {
                                return `${pad(adjustedDate.getHours())}:00`;
                            }
                            return ''; // 其他小时不显示，避免过于密集
                        case LightweightCharts.TickMarkType.Minute:
                            // 只有在非常非常放大的情况下才会显示分钟
                    return `${pad(adjustedDate.getHours())}:${pad(adjustedDate.getMinutes())}`; 
                        default:
                            // 对于更细的粒度或未知类型，可以显示HH:MM
                            return `${pad(adjustedDate.getHours())}:${pad(adjustedDate.getMinutes())}`;
                    }
                },
                // 统一时间轴配置，确保所有图表使用相同设置
                barSpacing: 6,           // 默认柱形间距
                minBarSpacing: 2,        // 最小柱形间距
                rightOffset: 5,          // 右侧偏移量
                lockVisibleTimeRangeOnResize: true, // 调整大小时锁定可见时间范围
                shiftVisibleRangeOnNewBar: false,   // 禁止新K线自动移动可见范围
                fixLeftEdge: false,      // 允许左侧边缘自由滚动
                fixRightEdge: false,     // 允许右侧边缘自由滚动
                allowEndOfTimeScaleVisibility: false, // 不允许时间轴末端的可见性，防止自动缩放
                rightBarStaysOnScroll: true, // 滚动时保持右侧柱形不变
            },
            leftPriceScale: {
                borderColor: '#2B2B43',
                scaleMargins: {
                    top: 0.1,
                    bottom: 0.1,
                },
                visible: true,
                borderVisible: true,
            },
            rightPriceScale: {
                borderColor: '#2B2B43',
                visible: false, // 隐藏右侧价格轴
            },
            handleScroll: {
                mouseWheel: true,
                pressedMouseMove: true,
                horzTouchDrag: true,
                vertTouchDrag: true,
            },
            handleScale: {
                axisPressedMouseMove: {
                    time: true,
                    price: true,
                },
                mouseWheel: true,
                pinch: true,
            },
            watermark: {
                visible: true,
                text: 'BinanceTradingReview',
                color: 'rgba(255, 255, 255, 0.1)',
                fontSize: 24,
                horzAlign: 'center',
                vertAlign: 'center',
            },
            localization: {
                locale: 'zh-CN',
                priceFormatter: (price) => {
                    return price.toFixed(2);
                },
            },
            kineticScroll: {
                mouse: true,
                touch: true,
            },
        };
        
        // 创建价格图表
        const priceChart = LightweightCharts.createChart(chartContainer, {
            ...commonChartOptions,
            timeScale: {
                ...commonChartOptions.timeScale,
                visible: false, // 在价格图表隐藏时间轴
            },
            handleScale: {
                axisPressedMouseMove: {
                    time: true,  // 允许横轴缩放
                    price: true, // 允许纵轴缩放
                },
                mouseWheel: true,
                pinch: true,
            },
            handleScroll: {
                mouseWheel: true,
                pressedMouseMove: true,
                horzTouchDrag: true,
                vertTouchDrag: true,
            },
        });

        // 将priceChart暴露为全局变量，以便导航功能可以访问
        window.priceChart = priceChart;
        console.log('价格图表已创建并设置为全局变量:', window.priceChart);
        
        // 创建成交量图表
        const volumeChart = LightweightCharts.createChart(volumeContainer, {
            ...commonChartOptions,
            timeScale: {
                ...commonChartOptions.timeScale,
                visible: true,
            },
            leftPriceScale: {
                ...commonChartOptions.leftPriceScale,
                scaleMargins: {
                    top: 0.2,
                    bottom: 0.2,
                },
                // 禁用价格缩放，只允许价格轴自适应
                autoScale: true,
                invertScale: false,
                alignLabels: true,
                borderVisible: true,
                entireTextOnly: true,
            },
            handleScale: {
                axisPressedMouseMove: {
                    time: true,  // 只允许横轴缩放
                    price: false, // 禁止纵轴缩放，避免冲突
                },
                mouseWheel: true, // 允许鼠标滚轮缩放
                pinch: true,      // 允许触摸缩放
            },
        });
        
        // 存储所有图表实例以便同步
        const allCharts = [priceChart, volumeChart];
        let rsiChart = null; // 在外部声明，以便后续可以添加到allCharts
        let macdChart = null; // 在外部声明
        
        // 添加K线图
        const candlestickSeries = priceChart.addCandlestickSeries({
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
            priceLineVisible: true,
            priceLineWidth: 1,
            priceLineColor: '#2196F3',
            priceLineStyle: LightweightCharts.LineStyle.Dashed,
            lastValueVisible: true,
            title: '价格',
            priceScaleId: 'left',  // 指定使用左侧价格轴
        });
        
        // 设置K线数据
        candlestickSeries.setData(chartData.candlestick);
        
        // 添加成交量图
        const volumeSeries = volumeChart.addHistogramSeries({
            color: '#26a69a',
            priceFormat: {
                type: 'volume',
                precision: 2,
                minMove: 0.01,
            },
            priceScaleId: 'left',  // 改为使用左侧价格轴
            title: '成交量',
        });
        
        // 设置成交量数据，并根据K线涨跌设置颜色
        const volumeData = chartData.volume.map((item, index) => {
            const candle = chartData.candlestick[index];
            return {
                time: item.time,
                value: item.volume,
                color: candle && candle.close >= candle.open ? '#26a69a' : '#ef5350',
            };
        });
        volumeSeries.setData(volumeData);
        
        // 添加EMA指标
        let emaSeries = null;
        if (showEma && chartData.ema20 && chartData.ema20.length > 0) {
            console.log('添加EMA指标...');
            emaSeries = priceChart.addLineSeries({
                color: '#f48fb1',
                lineWidth: 2,
                priceLineVisible: false,
                lastValueVisible: true,
                title: 'EMA20',
                priceScaleId: 'left', // 指定使用左侧价格轴
            });
            emaSeries.setData(chartData.ema20);
        }
        
        // 添加布林带
        let upperBandSeries = null;
        let middleBandSeries = null;
        let lowerBandSeries = null;
        
        if (showBollinger && chartData.upper_band && chartData.middle_band && chartData.lower_band) {
            console.log('添加布林带...');
            
            // 上轨
            upperBandSeries = priceChart.addLineSeries({
                color: '#90caf9',
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dashed,
                priceLineVisible: false,
                lastValueVisible: false,
                title: '上轨',
                priceScaleId: 'left', // 指定使用左侧价格轴
            });
            upperBandSeries.setData(chartData.upper_band);
            
            // 中轨 (SMA20)
            middleBandSeries = priceChart.addLineSeries({
                color: '#64b5f6',
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Solid,
                priceLineVisible: false,
                lastValueVisible: false,
                title: '中轨',
                priceScaleId: 'left', // 指定使用左侧价格轴
            });
            middleBandSeries.setData(chartData.middle_band);
            
            // 下轨
            lowerBandSeries = priceChart.addLineSeries({
                color: '#90caf9',
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dashed,
                priceLineVisible: false,
                lastValueVisible: false,
                title: '下轨',
                priceScaleId: 'left', // 指定使用左侧价格轴
            });
            lowerBandSeries.setData(chartData.lower_band);
        }
        
        // 创建RSI图表
        let rsiSeries = null;
        
        if (showRsi && rsiContainer && chartData.rsi && chartData.rsi.length > 0) {
            console.log('添加RSI指标...');
            
            rsiChart = LightweightCharts.createChart(rsiContainer, {
                ...commonChartOptions,
                height: 250,
                timeScale: {
                    ...commonChartOptions.timeScale,
                    visible: true,
                },
                leftPriceScale: {
                    ...commonChartOptions.leftPriceScale,
                    scaleMargins: {
                        top: 0.1,
                        bottom: 0.1,
                    },
                    autoScale: true,
                },
                layout: {
                    ...commonChartOptions.layout,
                    background: { color: '#151924' },
                    textColor: '#d1d4dc',
                },
                grid: {
                    ...commonChartOptions.grid,
                    horzLines: {
                        color: '#2B2B43',
                        style: LightweightCharts.LineStyle.Dotted,
                        visible: true,
                    },
                },
            });
            
            // 添加RSI线
            rsiSeries = rsiChart.addLineSeries({
                color: '#7b1fa2',
                lineWidth: 2,
                priceLineVisible: false,
                lastValueVisible: true,
                title: 'RSI(14)',
                priceScaleId: 'left', // 指定使用左侧价格轴
            });
            rsiSeries.setData(chartData.rsi);
            
            // 添加超买超卖参考线
            const rsiOverbought = rsiChart.addLineSeries({
                color: '#ef5350',
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dashed,
                priceLineVisible: false,
                lastValueVisible: false,
                priceScaleId: 'left', // 指定使用左侧价格轴
            });
            
            const rsiOversold = rsiChart.addLineSeries({
                color: '#26a69a',
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dashed,
                priceLineVisible: false,
                lastValueVisible: false,
                priceScaleId: 'left', // 指定使用左侧价格轴
            });
            
            // 设置超买超卖线的数据
            const rsiPeriod = chartData.rsi.map(point => ({
                time: point.time,
                value: 70, // 超买线
            }));
            
            const rsiOversoldData = chartData.rsi.map(point => ({
                time: point.time,
                value: 30, // 超卖线
            }));
            
            rsiOverbought.setData(rsiPeriod);
            rsiOversold.setData(rsiOversoldData);
            
            // 添加RSI指标到allCharts数组
            allCharts.push(rsiChart);
        }
        
        // 创建MACD图表
        let macdLineSeries = null;
        let signalLineSeries = null;
        let histogramSeries = null;
        
        if (showMacd && macdContainer && chartData.macd && chartData.signal && chartData.histogram) {
            console.log('添加MACD指标...');
            
            macdChart = LightweightCharts.createChart(macdContainer, {
                ...commonChartOptions,
                height: 250,
                timeScale: {
                    ...commonChartOptions.timeScale,
                    visible: true,
                },
                leftPriceScale: {
                    ...commonChartOptions.leftPriceScale,
                    scaleMargins: {
                        top: 0.1,
                        bottom: 0.1,
                    },
                    autoScale: true,
                },
                layout: {
                    ...commonChartOptions.layout,
                    background: { color: '#151924' },
                    textColor: '#d1d4dc',
                },
                grid: {
                    ...commonChartOptions.grid,
                    horzLines: {
                        color: '#2B2B43',
                        style: LightweightCharts.LineStyle.Dotted,
                        visible: true,
                    },
                },
            });
            
            // 添加MACD线
            macdLineSeries = macdChart.addLineSeries({
                color: '#2196F3',
                lineWidth: 2,
                priceLineVisible: false,
                lastValueVisible: true,
                title: 'MACD',
                priceScaleId: 'left', // 指定使用左侧价格轴
            });
            macdLineSeries.setData(chartData.macd);
            
            // 添加信号线
            signalLineSeries = macdChart.addLineSeries({
                color: '#FF9800',
                lineWidth: 2,
                priceLineVisible: false,
                lastValueVisible: true,
                title: '信号线',
                priceScaleId: 'left', // 指定使用左侧价格轴
            });
            signalLineSeries.setData(chartData.signal);
            
            // 添加直方图
            histogramSeries = macdChart.addHistogramSeries({
                color: '#26a69a',
                priceFormat: {
                    type: 'price',
                    precision: 6,
                },
                priceLineVisible: false,
                lastValueVisible: false,
                title: '直方图',
                priceScaleId: 'left', // 指定使用左侧价格轴
            });
            
            // 为直方图添加颜色
            const histogramData = chartData.histogram.map(item => ({
                time: item.time,
                value: item.value,
                color: item.value >= 0 ? '#26a69a' : '#ef5350',
            }));
            
            histogramSeries.setData(histogramData);
            
            // 添加零线
            const zeroLine = macdChart.addLineSeries({
                color: '#9e9e9e',
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dashed,
                priceLineVisible: false,
                lastValueVisible: false,
                priceScaleId: 'left', // 指定使用左侧价格轴
            });
            
            // 设置零线数据
            const zeroLineData = chartData.macd.map(point => ({
                time: point.time,
                value: 0,
            }));
            
            zeroLine.setData(zeroLineData);
            
            // 添加MACD指标到allCharts数组
            allCharts.push(macdChart);
        }
        
        // 通用同步函数 - 完全重写以确保更紧密的同步
        const syncTimeScale = (sourceChart, targetCharts) => {
            const sourceTimeScale = sourceChart.timeScale();
            
            // 创建一个处理函数，可以在需要时取消订阅
            const handler = sourceTimeScale.subscribeVisibleTimeRangeChange(() => {
                // 立即同步所有图表，不使用防抖或节流
                try {
                    // 获取源图表的可见范围和选项
                    const timeRange = sourceTimeScale.getVisibleRange();
                    const options = sourceTimeScale.options();
                    
                    if (timeRange && options) {
                        // 同步所有目标图表
                        targetCharts.forEach(targetChart => {
                            if (targetChart !== sourceChart) {
                                try {
                                    // 保持完全相同的选项和可见范围
                                    targetChart.timeScale().applyOptions(options);
                                targetChart.timeScale().setVisibleRange(timeRange);
                                } catch (err) {
                                    console.error('同步图表选项失败:', err);
                                }
                            }
                        });
                    }
                } catch (error) {
                    console.error('同步图表时间轴失败:', error);
                }
            });
            
            // 创建滚动同步处理器
            const scrollHandler = sourceTimeScale.subscribeVisibleLogicalRangeChange((logicalRange) => {
                if (logicalRange) {
                    try {
                        // 同步所有目标图表的逻辑范围
                        targetCharts.forEach(targetChart => {
                            if (targetChart !== sourceChart) {
                                // 使用逻辑范围同步可以更精确地匹配位置
                                targetChart.timeScale().setVisibleLogicalRange(logicalRange);
                            }
                        });
                    } catch (error) {
                        console.error('同步图表逻辑范围失败:', error);
                    }
                }
            });
            
            // 返回取消订阅的处理函数
            return {
                unsubscribe: () => {
                    if (handler && typeof handler.unsubscribe === 'function') {
                        handler.unsubscribe();
                    }
                    if (scrollHandler && typeof scrollHandler.unsubscribe === 'function') {
                        scrollHandler.unsubscribe();
                    }
                }
            };
        };

        // 优化的十字线同步函数
        const syncCrosshair = (sourceChart, targetCharts) => {
            // 创建一个可以取消的处理函数
            const handler = sourceChart.subscribeCrosshairMove(param => {
                // 立即同步所有图表，不使用防抖或节流
                try {
                    if (param && param.time) {
                        targetCharts.forEach(targetChart => {
                            if (targetChart !== sourceChart) {
                                // 检查API并使用正确的方法
                                if (typeof targetChart.setCrosshairPosition === 'function') {
                                    // 使用4.0.1版本的API
                                    targetChart.setCrosshairPosition(param.time, param.point ? param.point.y : null);
                                } else if (typeof targetChart.moveCrosshair === 'function') {
                                    // 旧版API
                                    targetChart.moveCrosshair({ time: param.time });
                                }
                            }
                        });
                    } else {
                        targetCharts.forEach(targetChart => {
                            if (targetChart !== sourceChart) {
                                // 检查API并使用正确的方法
                                if (typeof targetChart.clearCrosshairPosition === 'function') {
                                    targetChart.clearCrosshairPosition();
                                } else if (typeof targetChart.setCrosshairPosition === 'function') {
                                    // 4.0.1版本中可能需要传递null参数
                                    targetChart.setCrosshairPosition(null, null);
                                }
                            }
                        });
                    }
                } catch (error) {
                    console.error('同步十字线失败:', error);
                }
            });
            
            // 返回取消订阅的处理函数
            return {
                unsubscribe: () => {
                    if (handler && typeof handler.unsubscribe === 'function') {
                        handler.unsubscribe();
                    }
                }
            };
        };

        // 创建一个同步组
        const syncCharts = () => {
            // 清除之前可能存在的同步逻辑
            allCharts.forEach(chart => {
                // 如果存在，从chart实例上移除当前的同步状态
                if (chart._syncHandlers) {
                    chart._syncHandlers.forEach(handler => {
                        if (typeof handler.unsubscribe === 'function') {
                            handler.unsubscribe();
                        }
                    });
                    delete chart._syncHandlers;
                }
                
                // 移除所有可能已添加的事件监听器
                if (chart._eventListeners) {
                    chart._eventListeners.forEach(({ element, type, handler }) => {
                        element.removeEventListener(type, handler);
                    });
                    delete chart._eventListeners;
                }
            });
            
            // 初始化所有图表的处理器数组
            allCharts.forEach(chart => {
                chart._syncHandlers = [];
                chart._eventListeners = [];
            });
            
            // 为了解决同步问题，添加MACD和RSI到图表数组确保它们被同步
            if (rsiChart && !allCharts.includes(rsiChart)) {
                allCharts.push(rsiChart);
            }
            if (macdChart && !allCharts.includes(macdChart)) {
                allCharts.push(macdChart);
            }

            // 为了解决同步问题，强制同步所有图表状态
            const forceSyncAllCharts = () => {
                // 立即应用，不延迟
                const mainVisibleRange = priceChart.timeScale().getVisibleRange();
                const mainOptions = priceChart.timeScale().options();
                const mainLogicalRange = priceChart.timeScale().getVisibleLogicalRange();
                
                allCharts.forEach(chart => {
                    if (chart !== priceChart) {
                        try {
                            // 首先应用相同的选项
                            if (mainOptions) {
                                chart.timeScale().applyOptions(mainOptions);
                            }
                            
                            // 然后应用可见范围和逻辑范围，确保它们同步
                            if (mainVisibleRange) {
                                chart.timeScale().setVisibleRange(mainVisibleRange);
                            }
                            
                            if (mainLogicalRange) {
                                chart.timeScale().setVisibleLogicalRange(mainLogicalRange);
                            }
                        } catch (e) {
                            console.error('强制同步图表失败:', e);
                        }
                    }
                });
            };
            
            // 公开forceSyncAllCharts到全局作用域，以便其他函数可以使用
            window.forceSyncAllCharts = forceSyncAllCharts;
            
            // 严格的双向同步 - 所有图表都可以控制其他图表
            allCharts.forEach(chart => {
                const otherCharts = allCharts.filter(c => c !== chart);
                
                // 时间轴同步
                const timeScaleHandler = syncTimeScale(chart, otherCharts);
                if (timeScaleHandler) {
                    chart._syncHandlers.push(timeScaleHandler);
                    }
            
                // 十字线同步
                const crosshairHandler = syncCrosshair(chart, otherCharts);
            if (crosshairHandler) {
                    chart._syncHandlers.push(crosshairHandler);
            }
            });
            
            // 强制同步所有图表状态 - 确保初始状态一致
            setTimeout(() => {
                    forceSyncAllCharts();
            }, 100);
            
            // 监听主图表的滚轮和鼠标事件，确保更新后所有图表都同步
            const handleChartWheel = (e) => {
                // 为确保同步完整，稍后再次同步
                setTimeout(() => {
                    forceSyncAllCharts();
                }, 50);
            };
            
            // 为每个图表添加滚轮事件监听
            allCharts.forEach(chart => {
                let containerEl;
                
                // 安全地检查每个图表及其对应的容器
                if (chart === priceChart) { 
                    containerEl = chartContainer; 
                }
                else if (chart === volumeChart) { 
                    containerEl = volumeContainer; 
                }
                else if (chart === rsiChart && typeof rsiContainer !== 'undefined') { 
                    containerEl = rsiContainer; 
                }
                else if (chart === macdChart && typeof macdContainer !== 'undefined') { 
                    containerEl = macdContainer; 
                }
                
                if (containerEl) {
                    containerEl.addEventListener('wheel', handleChartWheel, { passive: true });
                    chart._eventListeners.push({ element: containerEl, type: 'wheel', handler: handleChartWheel });
            
                    // 监听鼠标按下事件（拖拽开始）
                    const handleMouseDown = (e) => {
                const mouseMoveHandler = (e) => {
                            // 在拖拽过程中同步图表
                            requestAnimationFrame(() => {
                        forceSyncAllCharts();
                            });
                };
                
                document.addEventListener('mousemove', mouseMoveHandler);
                
                const mouseUpHandler = () => {
                    document.removeEventListener('mousemove', mouseMoveHandler);
                    document.removeEventListener('mouseup', mouseUpHandler);
                    
                    // 在鼠标释放时，再次同步
                    setTimeout(() => {
                        forceSyncAllCharts();
                            }, 50);
                };
                
                document.addEventListener('mouseup', mouseUpHandler, { once: true });
            };
            
                    containerEl.addEventListener('mousedown', handleMouseDown);
                    chart._eventListeners.push({ element: containerEl, type: 'mousedown', handler: handleMouseDown });
                }
            });
        };

        // 全局调整图表大小函数
        const resizeAllCharts = () => {
            if (!allCharts || allCharts.length === 0) return;
            
            // 添加一个变量，避免重复更新
            if (window.isResizing) return;
            window.isResizing = true;
            
            // 标记调整大小进行中
            document.body.classList.add('charts-resizing');
            
            // 先保存主图表的设置
            let mainChartSettings = null;
            try {
                mainChartSettings = {
                    visibleRange: priceChart.timeScale().getVisibleRange(),
                    options: priceChart.timeScale().options(),
                    logicalRange: priceChart.timeScale().getVisibleLogicalRange()
                };
            } catch (e) {
                console.error('获取主图表设置失败:', e);
            }
            
            // 使用RAF确保平滑渲染
            requestAnimationFrame(() => {
                try {
                    // 暂停同步，避免改变大小时触发同步循环
                    allCharts.forEach(chart => {
                        if (chart._syncHandlers) {
                            chart._syncHandlers.forEach(handler => {
                                if (typeof handler.unsubscribe === 'function') {
                                    handler.unsubscribe();
                                }
                            });
                            chart._syncHandlers = [];
                        }
                        
                        // 也暂停事件监听
                        if (chart._eventListeners) {
                            chart._eventListeners.forEach(({ element, type, handler }) => {
                                element.removeEventListener(type, handler);
                            });
                            chart._eventListeners = [];
                        }
                    });
                    
                    // 改变每个图表的大小
                    allCharts.forEach(chart => {
                        let chartElement;
                        if (chart === priceChart) chartElement = chartContainer;
                        else if (chart === volumeChart) chartElement = volumeContainer;
                        else if (chart === rsiChart && typeof rsiContainer !== 'undefined') chartElement = rsiContainer;
                        else if (chart === macdChart && typeof macdContainer !== 'undefined') chartElement = macdContainer;
                        
                        if (chartElement) {
                            chart.resize(chartElement.clientWidth, chartElement.clientHeight);
                        }
                    });
                    
                    // 如果有保存的主图表设置，先应用到主图表，然后同步到其他图表
                    if (mainChartSettings) {
                        // 确保主图表设置正确
                        try {
                            // 主图表可能需要先设置选项
                            if (mainChartSettings.options) {
                                priceChart.timeScale().applyOptions(mainChartSettings.options);
                            }
                            
                            // 然后设置范围
                            if (mainChartSettings.visibleRange) {
                                priceChart.timeScale().setVisibleRange(mainChartSettings.visibleRange);
                            }
                            if (mainChartSettings.logicalRange) {
                                priceChart.timeScale().setVisibleLogicalRange(mainChartSettings.logicalRange);
                            }
                        } catch (e) {
                            console.error('应用主图表设置失败:', e);
                        }
                        
                        // 从主图表同步到其他图表
                        setTimeout(() => {
                            // 获取主图表当前的设置
                            const mainVisibleRange = priceChart.timeScale().getVisibleRange();
                            const mainOptions = priceChart.timeScale().options();
                            const mainLogicalRange = priceChart.timeScale().getVisibleLogicalRange();
                            
                            // 将主图表设置同步到其他图表
                            allCharts.forEach(chart => {
                                if (chart !== priceChart) {
                                    try {
                                        // 应用相同的选项
                                        if (mainOptions) {
                                            chart.timeScale().applyOptions(mainOptions);
                                        }
                                        
                                        // 应用相同的范围
                                        if (mainVisibleRange) {
                                            chart.timeScale().setVisibleRange(mainVisibleRange);
                                        }
                                        if (mainLogicalRange) {
                                            chart.timeScale().setVisibleLogicalRange(mainLogicalRange);
                }
            } catch (e) {
                                        console.error('应用从主图表同步的设置失败:', e);
                                    }
                                }
                            });
                        }, 50);
                    }
                } catch (error) {
                    console.error('调整图表大小失败:', error);
                    document.body.classList.remove('charts-resizing');
                    
                    // 出错时也尝试重新建立同步关系
                    setTimeout(() => {
                        syncCharts();
                    }, 50);
                } finally {
                    window.isResizing = false;
                }
            });
        };
        
        // 监听窗口大小变化 - 使用节流技术避免过多调用
        let resizeTimeout = null;
        window.addEventListener('resize', () => {
            if (resizeTimeout) clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                resizeAllCharts();
                resizeTimeout = null;
            }, 100);
        });
        
        // 创建价格图表图例
        const legendItems = [
            { text: '蜡烛图', color: '#26a69a' },
        ];
        
        if (showEma) {
            legendItems.push({ text: 'EMA20', color: '#f48fb1' });
        }
        
        if (showBollinger) {
            legendItems.push({ text: '布林带', color: '#90caf9' });
        }
        
        createLegend(priceChart, chartContainer, legendItems);
        
        // 创建成交量图表图例
        createLegend(volumeChart, volumeContainer, [
            { text: '成交量', color: '#26a69a' },
        ]);
        
        // 如果有RSI，创建RSI图表图例
        if (rsiChart && rsiContainer) {
            createLegend(rsiChart, rsiContainer, [
                { text: 'RSI(14)', color: '#7b1fa2' },
                { text: '超买(70)', color: '#ef5350' },
                { text: '超卖(30)', color: '#26a69a' },
        ]);
        }
        
        // 如果有MACD，创建MACD图表图例
        if (macdChart && macdContainer) {
            createLegend(macdChart, macdContainer, [
                { text: 'MACD', color: '#2196F3' },
                { text: '信号线', color: '#FF9800' },
                { text: '直方图', color: '#26a69a' },
            ]);
        }
        
        // 在这里添加全局样式
        addGlobalStyles();
        
        // 设置全屏变化监听器（只设置一次）
        const setupFullscreenChangeListener = () => {
            // 使用单例模式确保只添加一次监听器
            if (window.fullscreenListenerAdded) return;
            
            document.addEventListener('fullscreenchange', () => {
                const isFullscreen = !!document.fullscreenElement;
                
                // 更新所有全屏按钮图标
                const allButtons = document.querySelectorAll('.fullscreen-button');
                allButtons.forEach(btn => {
                    if (isFullscreen) {
                        btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z" fill="currentColor"/></svg>';
                    } else {
                        btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z" fill="currentColor"/></svg>';
                    }
                });
                
                // 全屏时应用特殊样式
                if (isFullscreen && document.fullscreenElement) {
                    Object.assign(document.fullscreenElement.style, {
                        background: '#151924',
                        padding: '20px',
                        boxSizing: 'border-box'
                    });
                } else if (container) {
                    Object.assign(container.style, {
                        background: '',
                        padding: '',
                        boxSizing: ''
                    });
                }
                
                // 全屏时重新调整所有图表
                setTimeout(() => {
                    resizeAllCharts();
                    // 重新同步所有图表
                    syncCharts();
                }, 100);
            });
            
            window.fullscreenListenerAdded = true;
        };

        // 设置全屏变化监听器
        setupFullscreenChangeListener();
        
        // 为所有图表添加交互（现在 allCharts 包含了所有活动图表）
        allCharts.forEach(chart => {
            let containerEl;
            let isMain = false;
            
            // 安全地检查每个图表及其对应的容器，确保变量已定义
            if (chart === priceChart) { 
                containerEl = chartContainer; 
                isMain = true; 
            }
            else if (chart === volumeChart) { 
                containerEl = volumeContainer; 
            }
            else if (chart === rsiChart && typeof rsiContainer !== 'undefined') { 
                containerEl = rsiContainer; 
            }
            else if (chart === macdChart && typeof macdContainer !== 'undefined') { 
                containerEl = macdContainer; 
            }
            
            if (containerEl) {
                addChartInteractions(chart, containerEl, isMain);
                
                // 每个图表都添加一个单独的全屏切换按钮
                if (isMain) {
                    const chartFullscreenBtn = createFullscreenButton(containerEl);
                    // 稍微调整主图表全屏按钮的位置，避免与其他元素重叠
                    chartFullscreenBtn.style.top = '40px';
                }
            }
        });
        
        // 为主容器添加全屏按钮
        createFullscreenButton(container);
        
        // 初始调整图表大小
        // 替换原来的简单resize函数
        // 删除旧的resizeChart定义，改用我们新的resizeAllCharts
        setTimeout(() => {
            resizeAllCharts();
            // 调整容器高度
            adjustContainerHeights();
        }, 100);
        
        // 创建交易标记和仓位连线 - 修正版本
        if (showTrades && tradesData && tradesData.length > 0) {
            try {
                console.log('正在添加仓位标记...', tradesData.length);
                
                // 存储标记数据
                const markers = [];
                const positionDetailsMap = {};
                
                // 重置全局仓位计数器，确保每次更新标记时都从1开始
                window.positionCounters = {};
                
                // 处理每个仓位
                tradesData.forEach(position => {
                    if (!position.open_time || !position.open_price) {
                        console.warn('仓位数据缺少开仓时间或价格:', position);
                        return;
                    }
                    
                    const positionId = position.position_id || `pos-${Math.random().toString(36).substr(2, 5)}`;
                    
                    // 修正时间格式 - 现在后端已经发送秒级时间戳，直接使用
                    const openTime = position.open_time;
                    console.log(`仓位 ${positionId} 开仓时间:`, openTime, new Date(openTime * 1000));
                    
                    // 从仓位ID或交易对中提取币种名称
                    let symbolName = '';
                    if (position.position_id && position.position_id.includes('/')) {
                        // 从仓位ID中提取，例如"SOL/USDT:USDT_1732201005590"
                        symbolName = position.position_id.split('/')[0];
                    } else if (position.symbol) {
                        // 直接使用仓位的symbol属性
                        symbolName = position.symbol.split('/')[0];
                    } else {
                        // 使用默认名称
                        symbolName = "币种";
                    }
                    
                    // 计算仓位序号 - 每次初始化时重置计数器
                    if (!window.positionCounters[symbolName]) {
                        window.positionCounters[symbolName] = 0;
                    }
                    
                    const positionIndex = ++window.positionCounters[symbolName];
                    
                    // 创建开仓标记 - 使用简化的文本格式
                    const openMarker = {
                        time: openTime, // 使用秒级时间戳匹配K线数据
                        position: 'belowBar',
                        color: position.side === 'long' ? '#4CAF50' : '#F44336',
                        shape: position.side === 'long' ? 'arrowUp' : 'arrowDown',
                        text: `${symbolName} 仓位${positionIndex} {开仓${position.side === 'long' ? '多' : '空'}}`,
                        id: `${positionId}_open`,
                        size: 1.2
                    };
                    
                    markers.push(openMarker);
                    
                    // 如果有平仓时间，创建平仓标记（不再创建连线）
                    if (position.close_time && position.close_price) {
                        const closeTime = position.close_time;
                        console.log(`仓位 ${positionId} 平仓时间:`, closeTime, new Date(closeTime * 1000));
                        
                        const closeMarker = {
                            time: closeTime, // 使用秒级时间戳匹配K线数据
                            position: 'aboveBar',
                            color: position.is_profit ? '#4CAF50' : '#F44336',
                            shape: position.side === 'long' ? 'arrowDown' : 'arrowUp',
                            text: `${symbolName} 仓位${positionIndex} {平仓${position.side === 'long' ? '多' : '空'}}`,
                            id: `${positionId}_close`,
                            size: 1.2
                        };
                        
                        markers.push(closeMarker);
                    }
                    
                    // 存储仓位详情
                    positionDetailsMap[`${positionId}_open`] = position;
                    if (position.close_time) {
                        positionDetailsMap[`${positionId}_close`] = position;
                    }
                });
                
                // 设置标记到主系列
                if (markers.length > 0) {
                    candlestickSeries.setMarkers(markers);
                    console.log(`已添加 ${markers.length} 个标记到K线图`);
                
                    // 延迟为标记添加data-marker-id属性，确保DOM元素已创建
                    // 增加延迟时间，并使用多次尝试的策略
                    const addMarkerIds = () => {
                        setTimeout(() => {
                            // 简化实现，只记录标记数量，不再查找和处理DOM元素
                            console.log(`已添加 ${markers.length} 个标记到K线图`);
                        }, 100);
                    };
                    
                    // 开始第一次尝试
                    addMarkerIds();
                    
                    // 添加基本标记信息到控制台
                    console.log(`总计添加了 ${markers.length} 个标记`);
                }
                
                // 监听十字线移动事件 - 检测标记悬停
                priceChart.subscribeCrosshairMove(param => {
                    if (!param.point) return;
                    
                    // 首先检查是否有hoveredObjectId，这通常包含标记ID
                    if (param.hoveredObjectId) {
                        console.log('悬停检测到hoveredObjectId:', param.hoveredObjectId);
                        
                        // 尝试从hoveredObjectId中提取仓位ID
                        let positionId = null;
                        if (param.hoveredObjectId.includes('_')) {
                            const parts = param.hoveredObjectId.split('_');
                            if (parts.length >= 2) {
                                positionId = parts[0] + "_" + parts[1]; // 使用前两部分作为positionId
                            }
                        }
                        
                        if (positionId) {
                            // 查找匹配的标记
                            let directMarker = null;
                            for (const marker of markers) {
                                if (marker.id && (marker.id.includes(positionId) || positionId.includes(marker.id))) {
                                    directMarker = marker;
                                    break;
                                }
                            }
                            
                            // 如果找到了标记，处理它
                            if (directMarker) {
                                const position = positionDetailsMap[directMarker.id];
                                if (position) {
                                    // 高亮显示标记
                                    document.querySelectorAll('.highlighted-marker').forEach(el => {
                                        el.classList.remove('highlighted-marker');
                                    });
                                    
                                    let markerElement = document.querySelector(`[data-marker-id="${directMarker.id}"]`);
                                    if (markerElement) {
                                        markerElement.classList.add('highlighted-marker');
                                    }
                                    
                                    // 更新仓位导航面板中的信息
                                    updatePositionInfoInNavigationPanel(position);
                                    
                                    // 确保导航面板可见
                                    const navigationController = document.getElementById('navigation-controller');
                                    if (navigationController) {
                                        navigationController.style.display = 'block';
                                        navigationController.style.opacity = '1';
                                    }
                                    
                                    return; // 处理完成，直接返回
                                }
                            }
                        }
                    }
                    
                    // 如果通过hoveredObjectId未找到标记，回退到原来的距离计算方法
                    let hoveredMarker = null;
                    const tolerance = 15; // 合理的容差
                    
                    // 遍历所有标记，找到距离鼠标最近的标记
                    for (const marker of markers) {
                        const markerCoordinate = priceChart.timeScale().timeToCoordinate(marker.time);
                        if (markerCoordinate === null) continue;
                        
                        const horizontalDistance = Math.abs(param.point.x - markerCoordinate);
                        
                        // 初步水平距离过滤
                        if (horizontalDistance > tolerance) continue;
                            
                        // 获取价格信息来判断垂直距离
                        try {
                            // 获取当前K线的信息来估算标记的垂直位置
                            const dataPoint = chartData.candlestick.find(d => d.time === marker.time);
                            if (!dataPoint) continue;
                            
                            // 根据标记位置选择合适的价格点（开仓在下方，平仓在上方）
                            const markerPrice = marker.position === 'belowBar' ? 
                                dataPoint.low * 0.9995 : dataPoint.high * 1.0005;
                            
                            // 将价格转换为坐标
                            const priceCoordinate = candlestickSeries.priceToCoordinate(markerPrice);
                            if (priceCoordinate === null) continue;
                            
                            // 检查垂直距离是否在合理范围内
                            const verticalDistance = Math.abs(param.point.y - priceCoordinate);
                            
                            if (horizontalDistance <= tolerance && verticalDistance <= 40) {
                                hoveredMarker = marker;
                                break;
                            }
                        } catch (e) {
                            // 如果价格转换失败，回退到只使用水平距离
                            if (horizontalDistance <= tolerance/2) { // 更严格的水平容差
                                hoveredMarker = marker;
                                break;
                            }
                        }
                    }
                    
                    if (hoveredMarker) {
                        const position = positionDetailsMap[hoveredMarker.id];
                        if (position) {
                            // 高亮显示标记 - 使用多种选择器尝试找到元素
                            let markerElement = document.querySelector(`[data-marker-id="${hoveredMarker.id}"]`);
                            if (!markerElement) {
                                // 尝试更通用的选择器
                                const markerTexts = document.querySelectorAll('.tv-lightweight-charts text');
                                for (const el of markerTexts) {
                                    if (el.textContent && el.textContent.includes(hoveredMarker.text.split('{')[0])) {
                                        markerElement = el.closest('g') || el;
                                        break;
                                    }
                                }
                            }
                            
                            if (markerElement) {
                                markerElement.classList.add('highlighted-marker');
                                // 添加调试日志
                                console.log(`高亮标记: ${hoveredMarker.id}, 文本: ${hoveredMarker.text}`);
                            } else {
                                console.warn(`未找到对应的标记元素: ${hoveredMarker.id}`);
                            }
                            
                            // 更新仓位导航面板中的信息
                            updatePositionInfoInNavigationPanel(position);
                            
                            // 确保导航面板可见
                            const navigationController = document.getElementById('navigation-controller');
                            if (navigationController) {
                                navigationController.style.display = 'block';
                                navigationController.style.opacity = '1';
                        }
                    } else {
                            console.warn(`在positionDetailsMap中未找到对应的仓位: ${hoveredMarker.id}`);
                        }
                    } else {
                        // 移除所有高亮
                        document.querySelectorAll('.highlighted-marker').forEach(el => {
                            el.classList.remove('highlighted-marker');
                        });
                    }
                });
                
                // 添加点击事件监听 - 在仓位导航面板显示详细信息
                priceChart.subscribeClick(param => {
                    if (!param.point || !param.time) return;
                    
                    // 添加调试日志
                    console.log('图表点击事件触发:', param);
                    
                    // 首先检查是否有hoveredObjectId，这通常包含标记ID
                    if (param.hoveredObjectId) {
                        console.log('检测到hoveredObjectId:', param.hoveredObjectId);
                        
                        // 尝试从hoveredObjectId中提取仓位ID
                        // 格式通常是 "Symbol_positionId_open/close"
                        let positionId = null;
                        if (param.hoveredObjectId.includes('_')) {
                            const parts = param.hoveredObjectId.split('_');
                            if (parts.length >= 2) {
                                // 使用前两部分作为positionId，例如 "SOL/USDT:USDT_1732023119751"
                                positionId = parts[0] + "_" + parts[1];
                                // 或者直接使用完整ID
                                // positionId = param.hoveredObjectId;
                            }
                        }
                        
                        if (positionId) {
                            console.log('提取的仓位ID:', positionId);
                            
                            // 查找匹配的标记
                            let directMarker = null;
                            for (const marker of markers) {
                                if (marker.id && (marker.id.includes(positionId) || positionId.includes(marker.id))) {
                                    directMarker = marker;
                                    console.log('通过ID匹配到标记:', marker);
                                    break;
                                }
                            }
                            
                            // 如果找到了标记，处理它
                            if (directMarker) {
                                const position = positionDetailsMap[directMarker.id];
                                if (position) {
                                    console.log('通过hoveredObjectId找到仓位:', position);
                                    
                                    // 高亮显示标记
                                    document.querySelectorAll('.highlighted-marker').forEach(el => {
                                        el.classList.remove('highlighted-marker');
                                    });
                                    
                                    // 更新仓位导航面板中的信息
                                    updatePositionInfoInNavigationPanel(position);
                                    
                                    // 确保导航面板可见
                                    const navigationController = document.getElementById('navigation-controller');
                                    if (navigationController) {
                                        navigationController.style.display = 'block';
                                        navigationController.style.opacity = '1';
                                    }
                                    
                                    return; // 处理完成，直接返回
                                }
                            }
                        }
                    }
                    
                    // 如果通过hoveredObjectId未找到标记，回退到原来的距离计算方法
                    let clickedMarker = null;
                    const tolerance = 20; // 增大容差，使点击更容易被检测到
                    
                    // 使用与悬停检测相同的逻辑查找被点击的标记
                    for (const marker of markers) {
                        const markerCoordinate = priceChart.timeScale().timeToCoordinate(marker.time);
                        if (markerCoordinate === null) continue;
                        
                        const horizontalDistance = Math.abs(param.point.x - markerCoordinate);
                        if (horizontalDistance > tolerance) continue;
                            
                        try {
                            // 获取当前K线的信息来估算标记的垂直位置
                            const dataPoint = chartData.candlestick.find(d => d.time === marker.time);
                            if (!dataPoint) continue;
                            
                            // 根据标记位置选择合适的价格点
                            const markerPrice = marker.position === 'belowBar' ? 
                                dataPoint.low * 0.9995 : dataPoint.high * 1.0005;
                            
                            // 将价格转换为坐标
                            const priceCoordinate = candlestickSeries.priceToCoordinate(markerPrice);
                            if (priceCoordinate === null) continue;
                            
                            // 检查垂直距离是否在合理范围内 - 增大容差
                            const verticalDistance = Math.abs(param.point.y - priceCoordinate);
                            
                            if (horizontalDistance <= tolerance && verticalDistance <= 50) {
                                clickedMarker = marker;
                                console.log('找到点击标记:', marker);
                                break;
                            }
                        } catch (e) {
                            console.warn('计算标记位置时出错:', e);
                            // 如果价格转换失败，回退到只使用水平距离
                            if (horizontalDistance <= tolerance/2) { // 更严格的水平容差
                                clickedMarker = marker;
                                console.log('使用水平距离找到点击标记:', marker);
                                break;
                            }
                        }
                    }
                    
                    if (clickedMarker) {
                        const position = positionDetailsMap[clickedMarker.id];
                        if (position) {
                            console.log('处理标记点击事件:', clickedMarker, position);
                            
                            // 高亮显示标记
                            document.querySelectorAll('.highlighted-marker').forEach(el => {
                                el.classList.remove('highlighted-marker');
                            });
                            
                            // 使用多种选择器尝试找到元素
                            let markerElement = document.querySelector(`[data-marker-id="${clickedMarker.id}"]`);
                            if (!markerElement) {
                                // 尝试更通用的选择器
                                const markerTexts = document.querySelectorAll('.tv-lightweight-charts text');
                                for (const el of markerTexts) {
                                    if (el.textContent && el.textContent.includes(clickedMarker.text.split('{')[0])) {
                                        markerElement = el.closest('g') || el;
                                        break;
                                    }
                                }
                            }
                            
                            if (markerElement) {
                                markerElement.classList.add('highlighted-marker');
                                console.log('标记元素已高亮');
                            } else {
                                console.warn(`未找到对应的标记元素: ${clickedMarker.id}`);
                            }
                            
                            // 更新仓位导航面板中的信息
                            updatePositionInfoInNavigationPanel(position);
                            
                            // 确保导航面板可见
                            const navigationController = document.getElementById('navigation-controller');
                            if (navigationController) {
                                navigationController.style.display = 'block';
                                navigationController.style.opacity = '1';
                            }
                        } else {
                            console.warn(`在positionDetailsMap中未找到对应的仓位: ${clickedMarker.id}`);
                        }
                    } else {
                        console.log('未找到被点击的标记');
                    }
                });
                
                // 辅助函数：更新仓位导航面板中的信息
                function updatePositionInfoInNavigationPanel(position) {
                    const positionInfoElement = document.getElementById('position-info');
                    if (!positionInfoElement) return;
                    
                    const isOpen = !position.close_time || position.close_time_formatted === '持仓中';
                    const positionType = position.side === 'long' ? '多头' : '空头';
                    const profitClass = position.profit >= 0 ? 'text-success' : 'text-danger';
                    
                    // 提取简短的仓位ID或币种名称
                    let symbolName = '';
                    if (position.position_id && position.position_id.includes('/')) {
                        symbolName = position.position_id.split('/')[0];
                    } else if (position.symbol) {
                        symbolName = position.symbol.split('/')[0];
                    } else {
                        symbolName = "币种";
                    }
                    
                    // 查找当前仓位的序号
                    let positionIndex = 0;
                    
                    // 方法1：从标记中查找序号信息
                    for (const marker of markers) {
                        if (marker.id && marker.id.includes(position.position_id)) {
                            // 标记文本格式为 "SOL 仓位1 {开仓多}"，提取仓位序号
                            const match = marker.text.match(/仓位(\d+)/);
                            if (match && match[1]) {
                                positionIndex = parseInt(match[1], 10);
                                break;
                            }
                        }
                    }
                    
                    // 方法2：如果未找到，使用全局仓位计数器的当前值
                    if (positionIndex === 0 && window.positionCounters && symbolName) {
                        positionIndex = window.positionCounters[symbolName] || 1;
                    }
                    
                    // 如果仍未找到序号，使用默认值
                    const positionIndexText = positionIndex > 0 ? `#${positionIndex}` : '';
                    
                    // 构建详细的仓位信息HTML
                    positionInfoElement.innerHTML = `
                        <div class="p-2 mb-2" style="background: ${position.profit >= 0 ? 'rgba(38, 166, 154, 0.1)' : 'rgba(239, 83, 80, 0.1)'}; border-radius: 6px;">
                            <div class="d-flex justify-content-between align-items-center mb-1">
                                <span class="fw-bold">${symbolName} ${positionIndexText}</span>
                                <span class="${profitClass} fw-bold">${positionType}</span>
                                        </div>
                            <div class="small text-info">${position.open_time_formatted}</div>
                            <div class="d-flex justify-content-between align-items-center">
                                <span class="small text-muted">开仓价:</span>
                                <span class="small fw-bold">${position.open_price}</span>
                                        </div>
                            ${!isOpen ? `
                                <div class="d-flex justify-content-between align-items-center">
                                    <span class="small text-muted">平仓价:</span>
                                    <span class="small fw-bold">${position.close_price}</span>
                                        </div>
                                <div class="d-flex justify-content-between align-items-center mt-1">
                                    <span class="small text-muted">利润:</span>
                                    <span class="${profitClass} fw-bold">${position.profit >= 0 ? '+' : ''}${Number(position.profit).toFixed(2)}</span>
                                </div>
                            ` : `
                                <div class="text-warning text-center small fw-bold mt-1">
                                    持仓中
                                        </div>
                                    `}
                                </div>
                            `;
                }
                
                console.log(`✅ 仓位标记添加完成: ${markers.length} 个标记`);
                
            } catch (error) {
                console.error('❌ 添加仓位标记时出错:', error);
            }
        }
        
        // 初始化导航面板的默认信息
        const positionInfoElement = document.getElementById('position-info');
        if (positionInfoElement) {
            positionInfoElement.innerHTML = `
                <div class="text-center p-2">
                    <div class="text-muted small mb-2">点击或悬停在交易标记上</div>
                    <div class="text-info small">显示仓位详细信息</div>
                </div>
            `;
        }
        
        // 应用新的同步机制
        syncCharts();
        
        // 添加处理函数确保足够的容器高度
        const adjustContainerHeights = () => {
            // 获取当前容器高度
            const containerHeight = container.offsetHeight;
            
            // 检查是否启用了RSI和MACD
            const hasRsi = showRsi && rsiContainer;
            const hasMacd = showMacd && macdContainer;
            
            // 在主图表和各指标图表之间分配高度
            if (hasRsi || hasMacd) {
                // 调整主图表和成交量图表的比例
                const mainChartPercentage = hasRsi && hasMacd ? 50 : 60;
                const volumePercentage = 20;
                
                // 计算RSI和MACD的高度百分比
                const indicatorPercentage = (100 - mainChartPercentage - volumePercentage) / (hasRsi && hasMacd ? 2 : 1);
                
                // 应用新的高度
                chartContainer.style.height = `calc(${mainChartPercentage}% - 5px)`;
                volumeContainer.style.height = `calc(${volumePercentage}% - 5px)`;
                
                if (hasRsi) {
                    rsiContainer.style.height = `calc(${indicatorPercentage}% - 5px)`;
                }
                
                if (hasMacd) {
                    macdContainer.style.height = `calc(${indicatorPercentage}% - 5px)`;
                }
                
                // 更新比例标签
                ratioLabel.textContent = `${mainChartPercentage}/${volumePercentage}/${indicatorPercentage}`;
            }
        };
        
        // 添加键盘箭头控制图表移动的功能
        const setupKeyboardNavigation = () => {
            // 防止重复添加事件监听器
            if (window.keyboardNavigationSetup) return;
            
            // 添加键盘事件监听
            document.addEventListener('keydown', (event) => {
                // 检查是否有活动的图表实例
                if (!window.priceChart) return;
                
                // 检查是否在输入框中输入 - 如果是则不处理键盘事件
                if (document.activeElement.tagName === 'INPUT' || 
                    document.activeElement.tagName === 'TEXTAREA' || 
                    document.activeElement.isContentEditable) {
                    return;
                }
                
                // 获取时间轴对象
                const timeScale = window.priceChart.timeScale();
                if (!timeScale) return;
                
                // 获取当前可见的逻辑范围
                const logicalRange = timeScale.getVisibleLogicalRange();
                if (!logicalRange) return;
                
                // 定义移动速度 - 每次移动的K线数量
                const moveSpeed = 1; // 改为1，每次只移动一根K线
                
                // 处理左右箭头键
                switch (event.key) {
                    case 'ArrowLeft':
                        // 向左移动图表
                        const newRangeLeft = {
                            from: logicalRange.from - moveSpeed,
                            to: logicalRange.to - moveSpeed
                        };
                        timeScale.setVisibleLogicalRange(newRangeLeft);
                        
                        // 同步其他图表
                        if (typeof window.forceSyncAllCharts === 'function') {
                            setTimeout(() => window.forceSyncAllCharts(), 0);
                        }
                        
                        // 阻止页面默认的左右滚动行为
                        event.preventDefault();
                        break;
                        
                    case 'ArrowRight':
                        // 向右移动图表
                        const newRangeRight = {
                            from: logicalRange.from + moveSpeed,
                            to: logicalRange.to + moveSpeed
                        };
                        timeScale.setVisibleLogicalRange(newRangeRight);
                        
                        // 同步其他图表
                        if (typeof window.forceSyncAllCharts === 'function') {
                            setTimeout(() => window.forceSyncAllCharts(), 0);
                        }
                        
                        // 阻止页面默认的左右滚动行为
                        event.preventDefault();
                        break;
                }
            });
            
            // 标记键盘导航已设置
            window.keyboardNavigationSetup = true;
            console.log('键盘导航功能已启用 (← → 方向键)');
        };
        
        // 应用新的同步机制
        syncCharts();
        
        // 设置键盘导航
        setupKeyboardNavigation();
        
        // 调用调整函数
        setTimeout(adjustContainerHeights, 100);
        
        // 在窗口大小改变时再次调整
        window.addEventListener('resize', () => {
            setTimeout(adjustContainerHeights, 100);
        });
        
        // 全局存储图表数据，供加载更多功能使用
        window.chartData = chartData;
        
        // 添加加载更多按钮和检测逻辑
        setupLoadMoreDetection(priceChart, chartContainer);
        
        // 返回null（Dash回调需要返回值）
        return null;
    },
    
    // 创建TradingView Lightweight Charts图表
    createChart: function(data, chartElementId, interactionElementId) {
        // 创建脚本元素加载TradingView Lightweight Charts库
        const libraryUrl = 'https://unpkg.com/lightweight-charts@3.8.0/dist/lightweight-charts.standalone.production.js';
        console.log('正在加载Lightweight Charts库：', libraryUrl);
        
        this.loadScript(libraryUrl)
            .then(() => {
                console.log('Lightweight Charts库加载成功');
                
                // 检查库是否成功加载
                if (typeof window.LightweightCharts === 'undefined') {
                    console.error('Lightweight Charts库未成功加载到window对象');
                    return;
                }
                
                // 创建图表
                const chartElement = document.getElementById(chartElementId);
                if (!chartElement) {
                    console.error('图表元素未找到:', chartElementId);
                    return;
                }
                
                try {
                    console.log('正在创建图表...');
                    
                    // 创建图表实例
                    const chart = window.LightweightCharts.createChart(chartElement, {
                        layout: {
                            background: { color: '#151924' },
                            textColor: '#d1d4dc',
                        },
                        grid: {
                            vertLines: { color: '#2B2B43' },
                            horzLines: { color: '#2B2B43' },
                        },
                        crosshair: {
                            mode: window.LightweightCharts.CrosshairMode.Normal,
                            vertLine: {
                                width: 1,
                                color: 'rgba(224, 227, 235, 0.5)',
                                style: 1,
                            },
                            horzLine: {
                                width: 1,
                                color: 'rgba(224, 227, 235, 0.5)',
                                style: 1,
                            },
                        },
                        timeScale: {
                            borderColor: '#2B2B43',
                            timeVisible: true,
                            secondsVisible: false,
                        },
                        leftPriceScale: {
                            borderColor: '#2B2B43',
                            visible: true
                        },
                        rightPriceScale: {
                            visible: false,
                        },
                        handleScroll: { mouseWheel: true, pressedMouseMove: true },
                        handleScale: { mouseWheel: true, pinch: true, axisPressedMouseMove: true },
                    });
                    
                    console.log('图表创建成功，添加K线系列...');
                    
                    // 检查candlestickSeries方法是否存在
                    if (typeof chart.addCandlestickSeries !== 'function') {
                        console.error('ERROR: chart.addCandlestickSeries不是一个函数');
                        console.log('可用的方法:', Object.keys(chart).filter(k => typeof chart[k] === 'function'));
                        
                        // 尝试使用替代方法
                        let mainSeries = null;
                        if (chart.addBarSeries) {
                            mainSeries = chart.addBarSeries({
                            upColor: '#26a69a',
                            downColor: '#ef5350',
                            wickUpColor: '#26a69a',
                            wickDownColor: '#ef5350',
                            });
                        }
                        
                        if (!mainSeries) {
                            console.error('无法创建K线图系列');
                            return;
                        }
                        
                        // 添加K线数据
                        if (data.candlestick && data.candlestick.length > 0) {
                            mainSeries.setData(data.candlestick);
                        }
                    } else {
                        // 创建主图表系列（K线图）
                        const mainSeries = chart.addCandlestickSeries({
                            upColor: '#26a69a',     // 上涨颜色：绿色
                            downColor: '#ef5350',   // 下跌颜色：红色
                            borderVisible: false,
                            wickUpColor: '#26a69a',
                            wickDownColor: '#ef5350',
                        });
                        
                        // 添加K线数据
                        if (data.candlestick && data.candlestick.length > 0) {
                            mainSeries.setData(data.candlestick);
                        }
                        
                        // 创建成交量图表
                        if (chart.addHistogramSeries) {
                            const volumePane = chart.addHistogramSeries({
                                color: '#26a69a',
                                priceFormat: {
                                    type: 'volume',
                                },
                                priceScaleId: 'volume', // 设置独立的价格轴ID
                                scaleMargins: {
                                    top: 0.8,
                                    bottom: 0,
                                },
                            });
                            
                            // 设置成交量数据
                            if (data.volume && data.volume.length > 0) {
                                // 添加颜色信息到成交量数据
                                const volumeData = data.volume.map((dataPoint, index) => {
                                    const isUp = index > 0 ? 
                                        data.candlestick[index].close >= data.candlestick[index].open : 
                                        true;
                                    return {
                                        time: dataPoint.time,
                                        value: dataPoint.volume,
                                        color: isUp ? '#26a69a' : '#ef5350',
                                    };
                                });
                                volumePane.setData(volumeData);
                            }
                        }
                        
                        // 添加SMA 20技术指标
                        if (data.sma20 && data.sma20.length > 0 && chart.addLineSeries) {
                            const sma20Series = chart.addLineSeries({
                                color: '#2196F3',
                                lineWidth: 2,
                                priceLineVisible: false,
                                lastValueVisible: false,
                                title: 'SMA 20',
                            });
                            sma20Series.setData(data.sma20);
                        }
                        
                        // 添加SMA 50技术指标
                        if (data.sma50 && data.sma50.length > 0 && chart.addLineSeries) {
                            const sma50Series = chart.addLineSeries({
                                color: '#FF9800',
                                lineWidth: 2,
                                priceLineVisible: false,
                                lastValueVisible: false,
                                title: 'SMA 50',
                            });
                            sma50Series.setData(data.sma50);
                        }
                        
                        // 添加EMA 20技术指标
                        if (data.ema20 && data.ema20.length > 0 && chart.addLineSeries) {
                            const ema20Series = chart.addLineSeries({
                                color: '#E91E63',
                                lineWidth: 2,
                                priceLineVisible: false,
                                lastValueVisible: false,
                                title: 'EMA 20',
                            });
                            ema20Series.setData(data.ema20);
                        }
                        
                        // 添加图表标题图例
                        const legend = document.createElement('div');
                        legend.style.position = 'absolute';
                        legend.style.top = '5px';
                        legend.style.left = '10px';
                        legend.style.zIndex = '1';
                        legend.style.color = '#d1d4dc';
                        legend.style.fontSize = '12px';
                        legend.innerHTML = `
                            <div style="display: inline-block; margin-right: 10px;">
                                <span style="display: inline-block; width: 10px; height: 10px; background: #2196F3; margin-right: 5px;"></span>
                                SMA 20
                            </div>
                            <div style="display: inline-block; margin-right: 10px;">
                                <span style="display: inline-block; width: 10px; height: 10px; background: #FF9800; margin-right: 5px;"></span>
                                SMA 50
                            </div>
                            <div style="display: inline-block;">
                                <span style="display: inline-block; width: 10px; height: 10px; background: #E91E63; margin-right: 5px;"></span>
                                EMA 20
                            </div>
                        `;
                        chartElement.appendChild(legend);
                        
                        // 处理交互事件 - 鼠标十字光标
                        if (chart.subscribeCrosshairMove) {
                            chart.subscribeCrosshairMove((param) => {
                                if (!param.time || param.point === undefined) {
                                    // 鼠标不在图表区域内
                                    return;
                                }
                                
                                // 找到对应时间点的蜡烛图数据
                                const candleData = param.seriesData && param.seriesData.get ? param.seriesData.get(mainSeries) : null;
                                const volumeData = volumePane && param.seriesData && param.seriesData.get ? param.seriesData.get(volumePane) : null;
                                
                                if (candleData) {
                                    // 格式化时间显示
                                    const dateStr = this.formatDate(new Date(param.time * 1000));
                                    
                                    // 创建交互数据对象
                                    const interactionData = {
                                        time: dateStr,
                                        price: param.point.y,
                                        open: candleData.open,
                                        high: candleData.high,
                                        low: candleData.low,
                                        close: candleData.close,
                                        volume: volumeData ? volumeData.value : 0
                                    };
                                    
                                    // 更新Dash中的交互元素
                                    const dashInteractionElement = document.getElementById('chart-interaction');
                                    if (dashInteractionElement) {
                                        dashInteractionElement.textContent = JSON.stringify(interactionData);
                                        
                                        // 触发内容变更事件，以便Dash可以检测到变化
                                        const event = new Event('change');
                                        dashInteractionElement.dispatchEvent(event);
                                    }
                                    
                                    // 同时更新我们自己创建的交互元素
                                    const interactionElement = document.getElementById(interactionElementId);
                                    if (interactionElement) {
                                        interactionElement.textContent = JSON.stringify(interactionData);
                                    }
                                }
                            });
                        }
                        
                        // 监听窗口大小变化，调整图表尺寸
                        if (window.ResizeObserver) {
                            const resizeObserver = new ResizeObserver(entries => {
                                if (entries.length === 0 || entries[0].target !== chartElement) {
                                    return;
                                }
                                const { width, height } = entries[0].contentRect;
                                chart.applyOptions({ width, height });
                            });
                            
                            resizeObserver.observe(chartElement);
                        }
                        
                        // 监听图表点击事件
                        if (chart.subscribeClick) {
                            chart.subscribeClick((param) => {
                                if (!param.time || param.point === undefined) {
                                    return;
                                }
                                
                                // 找到对应时间点的蜡烛图数据
                                const candleData = param.seriesData && param.seriesData.get ? param.seriesData.get(mainSeries) : null;
                                
                                if (candleData) {
                                    console.log('点击了K线:', {
                                        time: new Date(param.time * 1000),
                                        open: candleData.open,
                                        high: candleData.high,
                                        low: candleData.low,
                                        close: candleData.close
                                    });
                                }
                            });
                        }
                        
                        // 自适应初始视图
                        chart.timeScale().fitContent();
                    }
                } catch (error) {
                    console.error('创建图表时发生错误:', error);
                }
            })
            .catch(error => {
                console.error('加载Lightweight Charts库失败:', error);
            });
    },
    
    // 格式化日期函数
    formatDate: function(date) {
        return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
    },
    
    // 动态加载脚本
    loadScript: function(src) {
        return new Promise((resolve, reject) => {
            // 检查脚本是否已经加载
            if (document.querySelector(`script[src="${src}"]`)) {
                resolve();
                return;
            }
            
            const script = document.createElement('script');
            script.src = src;
            script.onload = () => {
                console.log(`Script loaded: ${src}`);
                resolve();
            };
            script.onerror = (e) => {
                console.error(`Script error: ${src}`, e);
                reject(e);
            };
            document.head.appendChild(script);
        });
    },

    // 添加导航到仓位的函数
    navigateToPosition: function(prevClicks, nextClicks, positionsData) {
        try {
            // 全局缩放设置 - 保存上一次的缩放级别
            if (typeof window.lastZoomLevel === 'undefined') {
                window.lastZoomLevel = {
                    barCount: 50,  // 默认显示50根K线
                    initialized: false
                };
            }
            
            // 检查是否有仓位数据
            if (!positionsData) {
                console.log('没有仓位数据可用');
                return 0;
            }
            
            const positions = JSON.parse(positionsData);
            if (!positions || positions.length === 0) {
                console.log('解析后的仓位数据为空');
                return 0;
            }
            
            console.log(`共找到 ${positions.length} 个仓位`);
            
            // 检查点击事件
            let isTriggered = false;
            let triggerId = '';
            
            // 初始化存储先前点击数
            if (typeof this.prevClicks === 'undefined') this.prevClicks = 0;
            if (typeof this.nextClicks === 'undefined') this.nextClicks = 0;
            
            if (this.prevClicks !== prevClicks && prevClicks) {
                isTriggered = true;
                triggerId = 'prev-position-button';
                this.prevClicks = prevClicks;
                console.log('触发前一个仓位按钮');
            } else if (this.nextClicks !== nextClicks && nextClicks) {
                isTriggered = true;
                triggerId = 'next-position-button';
                this.nextClicks = nextClicks;
                console.log('触发下一个仓位按钮');
            }
            
            if (!isTriggered) {
                console.log('没有检测到按钮点击事件');
                return 0;
            }
            
            // 全局变量保存当前索引
            if (typeof window.currentPositionIndex === 'undefined') {
                window.currentPositionIndex = 0;
            }
            
            // 根据按钮更新索引
            const oldIndex = window.currentPositionIndex;
            if (triggerId === 'prev-position-button') {
                window.currentPositionIndex = (window.currentPositionIndex - 1 + positions.length) % positions.length;
            } else if (triggerId === 'next-position-button') {
                window.currentPositionIndex = (window.currentPositionIndex + 1) % positions.length;
            }
            
            console.log(`仓位索引: ${oldIndex} -> ${window.currentPositionIndex}`);
            
            // 获取当前仓位
            const position = positions[window.currentPositionIndex];
            if (!position) {
                console.error('找不到当前索引的仓位数据');
                return 0;
            }
            
            // 获取时间戳并确保它是一个数字
            let timestamp = position.open_time;
            if (typeof timestamp === 'string') {
                timestamp = parseInt(timestamp, 10);
            }
            
            // 检查时间戳的有效性
            if (!timestamp || isNaN(timestamp)) {
                console.error('无效的时间戳:', timestamp);
                return 0;
            }
            
            // 确保时间戳格式正确 - 检查是否需要转换为秒级时间戳
            // Lightweight Charts期望秒级时间戳
            if (timestamp > 10000000000) {
                // 如果是毫秒时间戳，转换为秒级
                timestamp = Math.floor(timestamp / 1000);
                console.log('将毫秒时间戳转换为秒级:', timestamp);
            }
            
            console.log('仓位时间戳:', timestamp, '对应日期:', new Date(timestamp * 1000).toLocaleString());
            
            // 查找图表实例
            const chartContainer = document.getElementById('chart-container');
            if (!chartContainer) {
                console.error('找不到图表容器');
                return 0;
            }
            
            // 如果已经挂载了priceChart，尝试跳转到指定时间
            if (window.priceChart) {
                console.log('发现priceChart全局实例，准备跳转');
                
                // 获取当前图表时间尺度和K线周期
                const timeScale = window.priceChart.timeScale();
                if (!timeScale) {
                    console.error('无法获取时间尺度对象');
                    return 0;
                }
                
                // 获取数据源的时间精度
                let timeFrameMinutes = 60; // 默认为1小时
                const timeframeElement = document.getElementById('timeframe-dropdown');
                if (timeframeElement && timeframeElement.textContent) {
                    const tfText = timeframeElement.textContent;
                    if (tfText.includes('1分钟')) timeFrameMinutes = 1;
                    else if (tfText.includes('5分钟')) timeFrameMinutes = 5;
                    else if (tfText.includes('15分钟')) timeFrameMinutes = 15;
                    else if (tfText.includes('1小时')) timeFrameMinutes = 60;
                    else if (tfText.includes('4小时')) timeFrameMinutes = 240;
                    else if (tfText.includes('1天')) timeFrameMinutes = 1440;
                }
                
                console.log('检测到的K线周期:', timeFrameMinutes, '分钟');
                
                // 保存当前的可见范围，用于维持缩放级别
                const currentVisibleRange = timeScale.getVisibleRange();
                const currentLogicalRange = timeScale.getVisibleLogicalRange();
                console.log('当前可见范围:', currentVisibleRange);
                
                // 如果已有可见范围且是第一次跳转，记录缩放级别
                if (currentVisibleRange && !window.lastZoomLevel.initialized && currentVisibleRange.from && currentVisibleRange.to) {
                    const rangeDuration = currentVisibleRange.to - currentVisibleRange.from;
                    const estimatedBarCount = rangeDuration / (timeFrameMinutes * 60);
                    
                    // 记录当前缩放级别
                    window.lastZoomLevel.barCount = Math.max(20, Math.min(100, Math.round(estimatedBarCount)));
                    window.lastZoomLevel.initialized = true;
                    console.log('记录当前缩放级别:', window.lastZoomLevel.barCount, '根K线');
                }
                
                // 使用保存的缩放级别或默认值
                const klineCount = window.lastZoomLevel.barCount;
                
                // 计算前后的缓冲区时间 - 使用保存的缩放级别
                const bufferSeconds = timeFrameMinutes * 60 * klineCount / 2; // 每个方向显示一半K线
                
                // 只在首次跳转或没有当前范围时设置新范围
                const shouldSetNewRange = !currentVisibleRange || !window.lastZoomLevel.initialized;
                
                if (shouldSetNewRange) {
                    const timeRange = {
                        from: timestamp - bufferSeconds,  // 往前缓冲区
                        to: timestamp + bufferSeconds     // 往后缓冲区
                    };
                    
                    console.log('设置新的时间范围:', timeRange, '显示约', klineCount, '根K线');
                    
                    // 应用新的时间范围
                    setTimeout(() => {
                        try {
                            console.log('应用新的时间范围...');
                            timeScale.setVisibleRange(timeRange);
                            
                            // 设置后标记为已初始化
                            window.lastZoomLevel.initialized = true;
                        } catch (rangeErr) {
                            console.error('设置可见范围时出错:', rangeErr);
                        }
                    }, 0);
                } else {
                    console.log('保持当前缩放级别，仅滚动到目标位置');
                }
                
                // 测试时间戳是否可以转换为坐标
                const coordinate = timeScale.timeToCoordinate(timestamp);
                console.log('时间戳坐标:', coordinate);
                
                // 如果无法直接获取坐标，尝试找到最近的可用时间戳
                if (coordinate === null) {
                    console.log('时间戳坐标为null，尝试查找最近的可用时间点...');
                    
                    // 从图表获取可见的数据范围
                    const visibleRange = timeScale.getVisibleRange();
                    if (visibleRange) {
                        console.log('当前可见范围:', visibleRange);
                        
                        // 使用固定的时间范围，无需依赖坐标转换
                        const fixedRange = {
                            from: timestamp - 3600 * 24, // 向前1天
                            to: timestamp + 3600 * 24    // 向后1天
                        };
                        
                        console.log('使用固定范围:', fixedRange);
                        
                        // 设置可见范围
                        setTimeout(() => {
                            try {
                                timeScale.setVisibleRange(fixedRange);
                                console.log('已应用固定范围');
                            } catch (err) {
                                console.error('设置固定范围失败:', err);
                            }
                        }, 0);
                        
                        // 处理完毕，直接返回
                        return 0;
                    }
                }
                
                // 直接滚动到目标位置，保持当前缩放级别
                setTimeout(() => {
                    try {
                        // 再次测试时间戳转换
                        const updatedCoordinate = timeScale.timeToCoordinate(timestamp);
                        console.log('更新后的时间坐标:', updatedCoordinate);
                        
                        if (updatedCoordinate !== null) {
                            // 滚动到位置，0.5表示滚动到中心位置
                            console.log('滚动到指定位置而不改变缩放级别...');
                            timeScale.scrollToPosition(updatedCoordinate, 0.5);
                        } else {
                            console.error('无法将时间戳转换为坐标');
                            // 尝试使用时间戳直接滚动
                            console.log('尝试使用可见范围方法滚动...');
                            
                            // 获取当前的可见范围
                            const visibleLogicalRange = timeScale.getVisibleLogicalRange();
                            if (visibleLogicalRange) {
                                // 计算当前显示的K线数量
                                const visibleBars = visibleLogicalRange.to - visibleLogicalRange.from;
                                
                                // 使用setVisibleRange方法定位到目标时间
                                const newRange = {
                                    from: timestamp - (timeFrameMinutes * 60 * visibleBars / 2),
                                    to: timestamp + (timeFrameMinutes * 60 * visibleBars / 2)
                                };
                                
                                console.log('使用新的可见范围:', newRange);
                                timeScale.setVisibleRange(newRange);
                            } else {
                                // 如果无法获取当前的可见逻辑范围，使用默认范围
                                const defaultRange = {
                                    from: timestamp - (timeFrameMinutes * 60 * 25),
                                    to: timestamp + (timeFrameMinutes * 60 * 25)
                                };
                                console.log('使用默认范围:', defaultRange);
                                timeScale.setVisibleRange(defaultRange);
                            }
                        }
                        
                        // 高亮仓位标记
                        console.log('查找并高亮标记...');
                        // 找到与当前位置对应的K线图元素并突出显示它
                        const markers = document.querySelectorAll('.tv-lightweight-charts svg g text');
                        let found = false;
                        
                        markers.forEach(marker => {
                            // 移除所有之前的高亮
                            const parent = marker.parentElement;
                            if (parent) {
                                parent.classList.remove('highlighted-marker');
                            }
                            
                            // 检查是否是当前仓位的标记
                            if (marker.textContent && marker.textContent.includes(`仓位${window.currentPositionIndex + 1}`)) {
                                // 添加高亮效果
                                if (parent) {
                                    parent.classList.add('highlighted-marker');
                                    found = true;
                                    console.log('找到并高亮标记:', marker.textContent);
                                }
                            }
                        });
                        
                        if (!found) {
                            console.log('未找到匹配的标记元素，尝试备用查询选择器...');
                            // 尝试更宽松的查询选择器
                            const allTexts = document.querySelectorAll('.tv-lightweight-charts text');
                            allTexts.forEach(text => {
                                if (text.textContent && text.textContent.includes('仓位')) {
                                    console.log('找到标记文本:', text.textContent);
                                    if (text.textContent.includes(`仓位${window.currentPositionIndex + 1}`)) {
                                        let parent = text.parentElement;
                                        if (parent) {
                                            parent.classList.add('highlighted-marker');
                                            found = true;
                                            console.log('使用备用方法高亮标记:', text.textContent);
                                        }
                                    }
                                }
                            });
                        }
                    } catch (scrollErr) {
                        console.error('滚动到位置时出错:', scrollErr);
                    }
                }, 100);
                
                // 更新导航信息文本
                const positionInfoElement = document.getElementById('position-info');
                if (positionInfoElement) {
                    const positionTime = new Date(timestamp * 1000).toLocaleString();
                    const positionType = position.side === 'long' ? '多头' : '空头';
                    const profitClass = position.profit >= 0 ? 'text-success' : 'text-danger';
                    
                    // 提取简短的仓位ID或币种名称
                    let symbolName = '';
                    if (position.position_id && position.position_id.includes('/')) {
                        symbolName = position.position_id.split('/')[0];
                    } else if (position.symbol) {
                        symbolName = position.symbol.split('/')[0];
                    } else {
                        symbolName = "币种";
                    }
                    
                    // 查找当前仓位的序号
                    let positionIndex = 0;
                    
                    // 方法1：从标记中查找序号信息
                    for (const marker of markers) {
                        if (marker.id && marker.id.includes(position.position_id)) {
                            // 标记文本格式为 "SOL 仓位1 {开仓多}"，提取仓位序号
                            const match = marker.text.match(/仓位(\d+)/);
                            if (match && match[1]) {
                                positionIndex = parseInt(match[1], 10);
                                break;
                            }
                        }
                    }
                    
                    // 方法2：如果未找到，使用全局仓位计数器的当前值
                    if (positionIndex === 0 && window.positionCounters && symbolName) {
                        positionIndex = window.positionCounters[symbolName] || 1;
                    }
                    
                    // 如果仍未找到序号，使用默认值
                    const positionIndexText = positionIndex > 0 ? `#${positionIndex}` : '';
                    
                    positionInfoElement.innerHTML = `
                        <div class="p-2 mb-2" style="background: ${position.profit >= 0 ? 'rgba(38, 166, 154, 0.1)' : 'rgba(239, 83, 80, 0.1)'}; border-radius: 6px;">
                            <div class="d-flex justify-content-between align-items-center mb-1">
                                <span class="fw-bold">${symbolName} ${positionIndexText}</span>
                                <span class="${profitClass} fw-bold">${positionType}</span>
                            </div>
                            <div class="small text-info">${positionTime}</div>
                            <div class="d-flex justify-content-between align-items-center">
                                <span class="small text-muted">开仓价:</span>
                                <span class="small fw-bold">${position.open_price}</span>
                            </div>
                            ${!isOpen ? `
                                <div class="d-flex justify-content-between align-items-center">
                                    <span class="small text-muted">平仓价:</span>
                                    <span class="small fw-bold">${position.close_price}</span>
                                </div>
                                <div class="d-flex justify-content-between align-items-center mt-1">
                                    <span class="small text-muted">利润:</span>
                                    <span class="${profitClass} fw-bold">${position.profit >= 0 ? '+' : ''}${Number(position.profit).toFixed(2)}</span>
                                </div>
                            ` : `
                                <div class="text-warning text-center small fw-bold mt-1">
                                    持仓中
                                </div>
                            `}
                        </div>
                    `;
                    
                    console.log('已更新仓位信息面板');
                }
                
                console.log('已跳转到仓位时间点:', new Date(timestamp * 1000));
            } else {
                console.error('找不到价格图表实例 (window.priceChart)');
            }
            
            // 必须返回一个值，返回null会导致错误
            return 0;
        } catch (error) {
            console.error('仓位跳转出错:', error);
            return 0;
        }
    },
    
    // 通过编号跳转到指定仓位
    jumpToPositionByNumber: function(jumpClicks, positionNumber, positionsData) {
        try {
            // 检查必要参数
            if (!jumpClicks || !positionNumber || !positionsData) {
                console.log('缺少必要参数，跳过跳转');
                return 0;
            }
            
            console.log(`尝试跳转到仓位编号: ${positionNumber}`);
            
            // 解析仓位数据
            const positions = JSON.parse(positionsData);
            if (!positions || positions.length === 0) {
                console.log('没有可用的仓位数据');
                return 0;
            }
            
            // 确保编号在有效范围内
            const targetIndex = Math.min(Math.max(1, positionNumber), positions.length) - 1;
            
            // 更新全局索引
            if (typeof window.currentPositionIndex === 'undefined') {
                window.currentPositionIndex = 0;
            }
            window.currentPositionIndex = targetIndex;
            
            console.log(`跳转到仓位索引: ${targetIndex} (仓位编号: ${targetIndex + 1})`);
            
            // 获取目标仓位
            const position = positions[targetIndex];
            if (!position) {
                console.error('找不到指定编号的仓位');
                return 0;
            }
            
            // 获取时间戳并确保它是一个数字
            let timestamp = position.open_time;
            if (typeof timestamp === 'string') {
                timestamp = parseInt(timestamp, 10);
            }
            
            // 检查时间戳的有效性
            if (!timestamp || isNaN(timestamp)) {
                console.error('无效的时间戳:', timestamp);
                return 0;
            }
            
            // 确保时间戳格式正确 - 检查是否需要转换为秒级时间戳
            // Lightweight Charts期望秒级时间戳
            if (timestamp > 10000000000) {
                // 如果是毫秒时间戳，转换为秒级
                timestamp = Math.floor(timestamp / 1000);
                console.log('将毫秒时间戳转换为秒级:', timestamp);
            }
            
            console.log('仓位时间戳:', timestamp, '对应日期:', new Date(timestamp * 1000).toLocaleString());
            
            // 查找图表实例
            if (!window.priceChart) {
                console.error('找不到价格图表实例');
                return 0;
            }
            
            // 获取时间尺度
            const timeScale = window.priceChart.timeScale();
            if (!timeScale) {
                console.error('无法获取时间尺度对象');
                return 0;
            }
            
            // 获取数据源的时间精度
            let timeFrameMinutes = 60; // 默认为1小时
            const timeframeElement = document.getElementById('timeframe-dropdown');
            if (timeframeElement && timeframeElement.textContent) {
                const tfText = timeframeElement.textContent;
                if (tfText.includes('1分钟')) timeFrameMinutes = 1;
                else if (tfText.includes('5分钟')) timeFrameMinutes = 5;
                else if (tfText.includes('15分钟')) timeFrameMinutes = 15;
                else if (tfText.includes('1小时')) timeFrameMinutes = 60;
                else if (tfText.includes('4小时')) timeFrameMinutes = 240;
                else if (tfText.includes('1天')) timeFrameMinutes = 1440;
            }
            
            // 使用保存的缩放级别或默认值
            const klineCount = typeof window.lastZoomLevel !== 'undefined' && window.lastZoomLevel.barCount ? 
                window.lastZoomLevel.barCount : 50;
            
            // 计算缓冲区
            const bufferSeconds = timeFrameMinutes * 60 * klineCount / 2;
            
            // 设置可见范围
            const timeRange = {
                from: timestamp - bufferSeconds,
                to: timestamp + bufferSeconds
            };
            
            console.log('设置时间范围:', timeRange);
            
            // 应用时间范围
            setTimeout(() => {
                try {
                    timeScale.setVisibleRange(timeRange);
                    
                    // 高亮当前仓位标记
                    setTimeout(() => {
                        // 找到所有标记
                        const markers = document.querySelectorAll('.tv-lightweight-charts svg g text');
                        let found = false;
                        
                        markers.forEach(marker => {
                            // 移除所有之前的高亮
                            const parent = marker.parentElement;
                            if (parent) {
                                parent.classList.remove('highlighted-marker');
                            }
                            
                            // 检查是否是当前仓位的标记
                            if (marker.textContent && marker.textContent.includes(`仓位${targetIndex + 1}`)) {
                                // 添加高亮效果
                                if (parent) {
                                    parent.classList.add('highlighted-marker');
                                    found = true;
                                    console.log('找到并高亮标记:', marker.textContent);
                                }
                            }
                        });
                        
                        if (!found) {
                            console.log('未找到匹配的标记元素，尝试备用查询选择器...');
                            // 尝试更宽松的查询选择器
                            const allTexts = document.querySelectorAll('.tv-lightweight-charts text');
                            allTexts.forEach(text => {
                                if (text.textContent && text.textContent.includes('仓位')) {
                                    console.log('找到标记文本:', text.textContent);
                                    if (text.textContent.includes(`仓位${targetIndex + 1}`)) {
                                        let parent = text.parentElement;
                                        if (parent) {
                                            parent.classList.add('highlighted-marker');
                                            found = true;
                                            console.log('使用备用方法高亮标记:', text.textContent);
                                        }
                                    }
                                }
                            });
                        }
                        
                        // 更新导航信息文本
                        const positionInfoElement = document.getElementById('position-info');
                        if (positionInfoElement) {
                            const positionTime = new Date(timestamp * 1000).toLocaleString();
                            const positionType = position.side === 'long' ? '多头' : '空头';
                            const profitClass = position.profit >= 0 ? 'text-success' : 'text-danger';
                            
                            // 提取简短的仓位ID或币种名称
                            let symbolName = '';
                            if (position.position_id && position.position_id.includes('/')) {
                                symbolName = position.position_id.split('/')[0];
                            } else if (position.symbol) {
                                symbolName = position.symbol.split('/')[0];
                            } else {
                                symbolName = "币种";
                            }
                            
                            // 查找当前仓位的序号
                            let positionIndex = 0;
                            
                            // 方法1：从标记中查找序号信息
                            for (const marker of markers) {
                                if (marker.id && marker.id.includes(position.position_id)) {
                                    // 标记文本格式为 "SOL 仓位1 {开仓多}"，提取仓位序号
                                    const match = marker.text.match(/仓位(\d+)/);
                                    if (match && match[1]) {
                                        positionIndex = parseInt(match[1], 10);
                                        break;
                                    }
                                }
                            }
                            
                            // 方法2：如果未找到，使用全局仓位计数器的当前值
                            if (positionIndex === 0 && window.positionCounters && symbolName) {
                                positionIndex = window.positionCounters[symbolName] || 1;
                            }
                            
                            // 如果仍未找到序号，使用默认值
                            const positionIndexText = positionIndex > 0 ? `#${positionIndex}` : '';
                            
                            positionInfoElement.innerHTML = `
                                <div class="p-2 mb-2" style="background: ${position.profit >= 0 ? 'rgba(38, 166, 154, 0.1)' : 'rgba(239, 83, 80, 0.1)'}; border-radius: 6px;">
                                    <div class="d-flex justify-content-between align-items-center mb-1">
                                        <span class="fw-bold">${symbolName} ${positionIndexText}</span>
                                        <span class="${profitClass} fw-bold">${positionType}</span>
                                    </div>
                                    <div class="small text-info">${positionTime}</div>
                                    <div class="d-flex justify-content-between align-items-center">
                                        <span class="small text-muted">开仓价:</span>
                                        <span class="small fw-bold">${position.open_price}</span>
                                    </div>
                                    ${!position.close_time ? `
                                        <div class="text-warning text-center small fw-bold mt-1">
                                            持仓中
                                        </div>
                                    ` : `
                                        <div class="d-flex justify-content-between align-items-center">
                                            <span class="small text-muted">平仓价:</span>
                                            <span class="small fw-bold">${position.close_price}</span>
                                        </div>
                                        <div class="d-flex justify-content-between align-items-center mt-1">
                                            <span class="small text-muted">利润:</span>
                                            <span class="${profitClass} fw-bold">${position.profit >= 0 ? '+' : ''}${Number(position.profit).toFixed(2)}</span>
                                        </div>
                                    `}
                                </div>
                            `;
                            
                            console.log('已更新仓位信息面板');
                        }
                    }, 100);
                } catch (error) {
                    console.error('应用时间范围时出错:', error);
                }
            }, 0);
            
            // 清空输入框
            const inputElement = document.getElementById('position-number-input');
            if (inputElement) {
                inputElement.value = '';
            }
            
            console.log('已完成跳转处理');
            return 0;
        } catch (error) {
            console.error('编号跳转出错:', error);
            return 0;
        }
    },
    
    /**
     * 监听图表数据变化，恢复加载更多按钮状态
     * @param {Object} chartData - 图表数据
     * @returns {null} - 无返回值
     */
    resetLoadMoreButton: function(chartData) {
        // 图表数据更新后，重置加载更多按钮
        if (chartData) {
            try {
                const loadMoreBtn = document.querySelector('.load-more-button');
                if (loadMoreBtn && loadMoreBtn.innerText === '加载中...') {
                    loadMoreBtn.innerText = '加载更多';
                    loadMoreBtn.style.backgroundColor = 'rgba(33, 150, 243, 0.9)';
                    loadMoreBtn.style.cursor = 'pointer';
                    console.log('数据已更新，重置加载更多按钮状态');
                }
            } catch (e) {
                console.error('重置加载更多按钮状态时出错:', e);
            }
        }
        return null;
    }
}; 