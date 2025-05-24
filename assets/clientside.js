/**
 * TradingView Lightweight Charts 客户端交互脚本
 * 处理图表渲染、十字线、价格显示和交易标记
 */

if (!window.dash_clientside) {
    window.dash_clientside = {};
}

// 辅助函数 - 数字补零
const pad = (n) => n < 10 ? '0' + n : n;

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
    }, { passive: false });

    // 添加双击重置功能
    containerElement.addEventListener('dblclick', (e) => {
        const rect = containerElement.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        
        if (mouseX > rect.width - 50) {
            // 双击价格轴，重置价格范围
            const priceScale = chartInstance.priceScale('right');
            if (priceScale) {
                priceScale.applyOptions({
                    autoScale: true
                });
                // 自动缩放后恢复手动模式
                setTimeout(() => {
                    priceScale.applyOptions({
                        autoScale: false
                    });
                }, 10);
            }
        } else {
            // 双击图表主体，重置时间范围
            chartInstance.timeScale().fitContent();
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
    `;
    document.head.appendChild(style);
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
        volumeContainer.style.marginTop = '10px';
        
        // 创建分隔线，可拖动
        const dividerContainer = document.createElement('div');
        dividerContainer.style.width = '100%';
        dividerContainer.style.height = '10px';
        dividerContainer.style.position = 'relative';
        dividerContainer.style.cursor = 'ns-resize';
        dividerContainer.style.marginTop = '5px';
        dividerContainer.style.marginBottom = '5px';
        
        const divider = document.createElement('div');
        divider.style.width = '100%';
        divider.style.height = '1px';
        divider.style.background = '#758696';
        divider.style.borderStyle = 'dashed';
        divider.style.position = 'absolute';
        divider.style.top = '50%';
        divider.style.transform = 'translateY(-50%)';
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
                    const date = new Date(time * 1000);
                    
                    // 使用 LightweightCharts 提供的 TickMarkType 来决定格式
                    // TickMarkType: Year = 0, Month = 1, Day = 2, Hour = 3, Minute = 4, Second = 5
                    switch (tickMarkType) {
                        case LightweightCharts.TickMarkType.Year:
                            return date.getFullYear().toString();
                        case LightweightCharts.TickMarkType.Month:
                            // 使用Intl API来获取本地化的月份名称缩写
                            return new Intl.DateTimeFormat(locale, { month: 'short' }).format(date);
                        case LightweightCharts.TickMarkType.Day:
                            return pad(date.getDate());
                        case LightweightCharts.TickMarkType.Hour:
                            // 每4小时标记一个小时文本，其他小时留空或显示更简略标记
                            if (date.getHours() % 4 === 0) {
                                return `${pad(date.getHours())}:00`;
                            }
                            return ''; // 其他小时不显示，避免过于密集
                        case LightweightCharts.TickMarkType.Minute:
                            // 只有在非常非常放大的情况下才会显示分钟
                    return `${pad(date.getHours())}:${pad(date.getMinutes())}`; 
                        default:
                            // 对于更细的粒度或未知类型，可以显示HH:MM
                            return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
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
            rightPriceScale: {
                borderColor: '#2B2B43',
                scaleMargins: {
                    top: 0.1,
                    bottom: 0.1,
                },
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
        
        // 创建成交量图表
        const volumeChart = LightweightCharts.createChart(volumeContainer, {
            ...commonChartOptions,
            timeScale: {
                ...commonChartOptions.timeScale,
                visible: true,
            },
            rightPriceScale: {
                ...commonChartOptions.rightPriceScale,
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
            priceScaleId: 'volume',
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
        
        // 通用同步函数 - 完全重写以确保更紧密的同步
        const syncTimeScale = (sourceChart, targetCharts) => {
            const sourceTimeScale = sourceChart.timeScale();
            
            // 创建一个处理函数，可以在需要时取消订阅
            const handler = sourceTimeScale.subscribeVisibleTimeRangeChange(() => {
                // 立即同步所有图表，不使用防抖或节流
                try {
                    // 获取源图表的可见范围和缩放级别
                    const timeRange = sourceTimeScale.getVisibleRange();
                    const barSpacing = sourceTimeScale.barSpacing();
                    
                    if (timeRange && barSpacing) {
                        // 同步所有目标图表
                        targetCharts.forEach(targetChart => {
                            if (targetChart !== sourceChart) {
                                // 保持完全相同的缩放级别和可见范围
                                // 注意：顺序很重要 - 先设置bar spacing再设置可见范围
                                targetChart.timeScale().setBarSpacing(barSpacing);
                                targetChart.timeScale().setVisibleRange(timeRange);
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
            
            // 严格的单向同步 - 只从主图表同步到辅助图表
            // 禁用从辅助图表到主图表的同步，以避免循环
            const mainTimeScaleHandler = syncTimeScale(priceChart, 
                allCharts.filter(c => c !== priceChart)
            );
            if (mainTimeScaleHandler) {
                priceChart._syncHandlers.push(mainTimeScaleHandler);
            }

            // 为了解决同步问题，强制同步所有图表状态
            const forceSyncAllCharts = () => {
                // 立即应用，不延迟
                const mainVisibleRange = priceChart.timeScale().getVisibleRange();
                const mainBarSpacing = priceChart.timeScale().barSpacing();
                const mainLogicalRange = priceChart.timeScale().getVisibleLogicalRange();
                
                allCharts.forEach(chart => {
                    if (chart !== priceChart) {
                        try {
                            // 首先设置图表的barSpacing
                            if (mainBarSpacing) {
                                chart.timeScale().setBarSpacing(mainBarSpacing);
                            }
                            
                            // 然后同时应用可见范围和逻辑范围，确保它们同步
                            if (mainVisibleRange) {
                                chart.timeScale().setVisibleRange(mainVisibleRange);
                            }
                            
                            if (mainLogicalRange) {
                                chart.timeScale().setVisibleLogicalRange(mainLogicalRange);
                            }
                            
                            // 确保所有图表的timeScale有相同的选项
                            const srcOptions = priceChart.timeScale().options();
                            chart.timeScale().applyOptions(srcOptions);
                        } catch (e) {
                            console.error('强制同步图表失败:', e);
                        }
                    }
                });
            };
            
            // 公开forceSyncAllCharts到全局作用域，以便其他函数可以使用
            window.forceSyncAllCharts = forceSyncAllCharts;
            
            // 监听所有辅助图表的操作，但不让它们控制主图表
            // 而是在它们被操作时，强制它们与主图表同步
            const handleSecondaryChartInteraction = (e) => {
                // 为了避免循环，在操作辅助图表后，强制设置为主图表的状态
                setTimeout(() => {
                    forceSyncAllCharts();
                }, 0);
            };
            
            // 在所有辅助图表上添加交互监听器
            allCharts.forEach(chart => {
                if (chart !== priceChart) {
                    const element = chart.chartElement || (
                        chart === volumeChart ? volumeContainer : 
                        chart === rsiChart ? rsiContainer : 
                        chart === macdChart ? macdContainer : null
                    );
                    
                    if (element) {
                        // 监听滚轮事件
                        const wheelHandler = (e) => {
                            handleSecondaryChartInteraction(e);
                        };
                        element.addEventListener('wheel', wheelHandler, { passive: true });
                        chart._eventListeners.push({ element, type: 'wheel', handler: wheelHandler });
                        
                        // 监听鼠标按下事件，可能是拖拽开始
                        const mouseDownHandler = (e) => {
                            const mouseMoveHandler = (e) => {
                                handleSecondaryChartInteraction(e);
                            };
                            
                            document.addEventListener('mousemove', mouseMoveHandler);
                            
                            const mouseUpHandler = () => {
                                document.removeEventListener('mousemove', mouseMoveHandler);
                                document.removeEventListener('mouseup', mouseUpHandler);
                                
                                // 在鼠标释放时，再次同步
                                handleSecondaryChartInteraction(e);
                            };
                            
                            document.addEventListener('mouseup', mouseUpHandler, { once: true });
                        };
                        
                        element.addEventListener('mousedown', mouseDownHandler);
                        chart._eventListeners.push({ element, type: 'mousedown', handler: mouseDownHandler });
                    }
                }
            });
            
            // 只有主图表的十字线同步到其他图表
            // 禁用从辅助图表到主图表的十字线同步，避免潜在的循环
            const crosshairHandler = syncCrosshair(priceChart, 
                allCharts.filter(c => c !== priceChart)
            );
            if (crosshairHandler) {
                priceChart._syncHandlers.push(crosshairHandler);
            }
            
            // 确保所有图表初始设置一致
            setTimeout(() => {
                try {
                    forceSyncAllCharts();
                } catch (error) {
                    console.error('初始同步图表设置失败:', error);
                }
            }, 100);
            
            // 主图表的特殊处理
            // 监听主图表的滚轮和鼠标事件，确保更新后所有图表都同步
            const handleMainChartWheel = (e) => {
                // 立即同步，不延迟
                forceSyncAllCharts();
                
                // 为确保同步完整，0毫秒后再次同步
                setTimeout(() => {
                    forceSyncAllCharts();
                }, 0);
                
                // 添加额外的延迟同步以确保完全同步
                setTimeout(() => {
                    forceSyncAllCharts();
                }, 50);
            };
            
            // 监听主图表容器的滚轮事件
            chartContainer.addEventListener('wheel', handleMainChartWheel, { passive: true });
            priceChart._eventListeners.push({ element: chartContainer, type: 'wheel', handler: handleMainChartWheel });
            
            // 监听主图表的鼠标按下事件（拖拽开始）
            const handleMainChartMouseDown = (e) => {
                const mouseMoveHandler = (e) => {
                    // 立即同步，不延迟
                    forceSyncAllCharts();
                    
                    // 为确保同步完整，0毫秒后再次同步
                    setTimeout(() => {
                        forceSyncAllCharts();
                    }, 0);
                    
                    // 添加额外的延迟同步以确保完全同步
                    setTimeout(() => {
                        forceSyncAllCharts();
                    }, 50);
                };
                
                document.addEventListener('mousemove', mouseMoveHandler);
                
                const mouseUpHandler = () => {
                    document.removeEventListener('mousemove', mouseMoveHandler);
                    document.removeEventListener('mouseup', mouseUpHandler);
                    
                    // 在鼠标释放时，再次同步
                    setTimeout(() => {
                        forceSyncAllCharts();
                    }, 0);
                };
                
                document.addEventListener('mouseup', mouseUpHandler, { once: true });
            };
            
            chartContainer.addEventListener('mousedown', handleMainChartMouseDown);
            priceChart._eventListeners.push({ element: chartContainer, type: 'mousedown', handler: handleMainChartMouseDown });
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
                    barSpacing: priceChart.timeScale().barSpacing(),
                    logicalRange: priceChart.timeScale().getVisibleLogicalRange(),
                    options: priceChart.timeScale().options()
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
                            
                            // 然后设置缩放和范围
                            if (mainChartSettings.barSpacing) {
                                priceChart.timeScale().setBarSpacing(mainChartSettings.barSpacing);
                            }
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
                            const mainBarSpacing = priceChart.timeScale().barSpacing();
                            const mainLogicalRange = priceChart.timeScale().getVisibleLogicalRange();
                            const mainOptions = priceChart.timeScale().options();
                            
                            // 将主图表设置同步到其他图表
                            allCharts.forEach(chart => {
                                if (chart !== priceChart) {
                                    try {
                                        // 应用相同的选项
                                        if (mainOptions) {
                                            chart.timeScale().applyOptions(mainOptions);
                                        }
                                        
                                        // 应用相同的缩放和范围
                                        if (mainBarSpacing) {
                                            chart.timeScale().setBarSpacing(mainBarSpacing);
                                        }
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
                            
                            // 重新建立同步关系
                            syncCharts();
                            document.body.classList.remove('charts-resizing');
                        }, 50);
            } else {
                        // 如果没有主图表设置，也重新建立同步关系
                        setTimeout(() => {
                            syncCharts();
                            document.body.classList.remove('charts-resizing');
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
        createLegend(priceChart, chartContainer, [
            { label: 'EMA20', color: '#f48fb1' },
            { label: '上涨', color: '#26a69a' },
            { label: '下跌', color: '#ef5350' },
        ]);
        
        // 创建成交量图表图例
        createLegend(volumeChart, volumeContainer, [
            { label: '成交量', color: '#26a69a' },
        ]);
        
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
                        btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z" fill="currentColor"/></svg>';
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
        setTimeout(resizeAllCharts, 100);
        
        // 创建交易标记 - 确保正确添加到图表
        if (showTrades && tradesData && tradesData.length > 0) {
            try {
                console.log('正在添加交易标记...', tradesData.length);
                
                // 创建一个数组来存储所有标记
                const markers = [];
                
                // 将交易标记添加到图表
                tradesData.forEach(trade => {
                    if (!trade.time || !trade.price) {
                        console.warn('交易数据缺少时间或价格:', trade);
                        return;
                    }
                    
                    // 创建简单的箭头标记
                    const marker = {
                        time: trade.time,
                        position: trade.side === 'buy' ? 'belowBar' : 'aboveBar', // 买入标记在下方，卖出标记在上方
                        color: trade.side === 'buy' ? '#26a69a' : '#ef5350',
                        shape: trade.side === 'buy' ? 'arrowUp' : 'arrowDown',
                        size: 2, // 增大标记大小，提高可点击/悬停区域
                        text: trade.side === 'buy' ? '买' : '卖', // 添加简短文本标识
                    };
                    
                    // 添加到标记数组
                    markers.push(marker);
                });
                
                // 一次性设置所有标记
                if (markers.length > 0) {
                    console.log('设置交易标记:', markers.length);
                    candlestickSeries.setMarkers(markers);
                }
                
                // 刷新主图表，确保标记显示
                        setTimeout(() => {
                    const currRange = priceChart.timeScale().getVisibleRange();
                    if (currRange) {
                        priceChart.timeScale().setVisibleRange({
                            from: currRange.from,
                            to: currRange.to
                        });
                    }
                }, 100);
            } catch (error) {
                console.error('添加交易标记失败:', error);
            }
        }
        
        // 应用新的同步机制
        syncCharts();
        
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
                        rightPriceScale: {
                            borderColor: '#2B2B43',
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
                        const mainSeries = chart.addBarSeries ? chart.addBarSeries({
                            upColor: '#26a69a',
                            downColor: '#ef5350',
                            wickUpColor: '#26a69a',
                            wickDownColor: '#ef5350',
                        }) : null;
                        
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
    }
}; 