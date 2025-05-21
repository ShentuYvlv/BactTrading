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
        
        dividerContainer.addEventListener('mousedown', function(e) {
            isDragging = true;
            startY = e.clientY;
            initialChartHeight = chartContainer.offsetHeight;
            containerHeight = container.offsetHeight - dividerContainer.offsetHeight;
            
            document.body.style.cursor = 'ns-resize';
            e.preventDefault();
        });
        
        document.addEventListener('mousemove', function(e) {
            if (isDragging) {
                const delta = e.clientY - startY;
                const newChartHeight = Math.max(50, Math.min(containerHeight - 50, initialChartHeight + delta));
                
                chartRatio = newChartHeight / containerHeight;
                
                chartContainer.style.height = `calc(${Math.round(chartRatio * 100)}% - 5px)`;
                volumeContainer.style.height = `calc(${Math.round((1 - chartRatio) * 100)}% - 5px)`;
                
                ratioLabel.textContent = `${Math.round(chartRatio * 100)}/${Math.round((1 - chartRatio) * 100)}`;
                
                // 重新调整图表
                if (priceChart && volumeChart) {
                    priceChart.resize(chartContainer.clientWidth, chartContainer.clientHeight);
                    volumeChart.resize(volumeContainer.clientWidth, volumeContainer.clientHeight);
                }
                
                e.preventDefault();
            }
        });
        
        document.addEventListener('mouseup', function() {
            if (isDragging) {
                isDragging = false;
                document.body.style.cursor = '';
            }
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
                // 增加一个选项，使得在显示范围较小时，主要刻度可以是小时
                minBarSpacing: 5, // 调整这个值可能会影响刻度的密集程度和类型
                rightOffset: 0, // 确保图表右侧没有额外的偏移量，尝试解决K线末端缩放问题
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
                    time: false,
                    price: true,
                },
                mouseWheel: true, // <--- 启用滚轮缩放
                pinch: true,
            },
            handleScroll: {
                mouseWheel: true, // <--- 启用滚轮滚动
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
            },
            handleScale: {
                axisPressedMouseMove: {
                    time: false,
                    price: false,
                },
                mouseWheel: true,
                pinch: true,
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
        
        // 通用同步函数
        const syncTimeScale = (sourceChart, targetCharts) => {
            const sourceTimeScale = sourceChart.timeScale();
            sourceTimeScale.subscribeVisibleTimeRangeChange(() => {
                const timeRange = sourceTimeScale.getVisibleRange();
                if (timeRange) {
                    targetCharts.forEach(targetChart => {
                        if (targetChart !== sourceChart) {
                            targetChart.timeScale().setVisibleRange(timeRange);
                        }
                    });
                }
            });
        };

        const syncCrosshair = (sourceChart, targetCharts, seriesArray) => {
            sourceChart.subscribeCrosshairMove(param => {
                if (param && param.time) {
                    targetCharts.forEach((targetChart, index) => {
                        if (targetChart !== sourceChart) {
                            // 对于目标图表，我们只需要传递时间来移动十字线
                            // 系列信息 (seriesArray[index]) 在这里可能不需要，除非目标图表有特殊处理
                            targetChart.moveCrosshair({ time: param.time });
                        }
                    });
                } else {
                    targetCharts.forEach(targetChart => {
                        if (targetChart !== sourceChart) {
                            targetChart.crosshairMoved(null); // 或者 targetChart.clearCrosshairPosition(); 根据API
                        }
                    });
                }
            });
        };

        // 为 priceChart 和 volumeChart 设置双向同步
        syncTimeScale(priceChart, [volumeChart]);
        syncTimeScale(volumeChart, [priceChart]);
        syncCrosshair(priceChart, [volumeChart]);
        syncCrosshair(volumeChart, [priceChart]);
        
        // 添加更多技术指标
        // 如果启用了EMA，添加EMA线
        let ema20Series = null;
        if (showEma && chartData.ema20 && chartData.ema20.length > 0) {
            ema20Series = priceChart.addLineSeries({
                color: '#f48fb1',
                lineWidth: 2,
                priceLineVisible: false,
                lastValueVisible: true,
                crosshairMarkerVisible: true,
                crosshairMarkerRadius: 4, 
                title: 'EMA20',
            });
            ema20Series.setData(chartData.ema20);
        }
        
        // 添加布林带（如果有数据并且启用了显示）
        let upperBandSeries = null;
        let middleBandSeries = null;
        let lowerBandSeries = null;
        
        if (showBollinger && chartData.upper_band && chartData.upper_band.length > 0) {
            upperBandSeries = priceChart.addLineSeries({
                color: 'rgba(76, 175, 80, 0.5)',
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dotted,
                priceLineVisible: false,
                lastValueVisible: false,
                title: '上轨',
            });
            upperBandSeries.setData(chartData.upper_band);
            
            middleBandSeries = priceChart.addLineSeries({
                color: 'rgba(156, 39, 176, 0.5)',
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Solid,
                priceLineVisible: false,
                lastValueVisible: false,
                title: 'SMA20',
            });
            middleBandSeries.setData(chartData.middle_band);
            
            lowerBandSeries = priceChart.addLineSeries({
                color: 'rgba(76, 175, 80, 0.5)',
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dotted,
                priceLineVisible: false,
                lastValueVisible: false,
                title: '下轨',
            });
            lowerBandSeries.setData(chartData.lower_band);
        }
        
        // 添加 RSI 指标（在单独的容器中）
        if (showRsi && chartData.rsi && chartData.rsi.length > 0) {
            // 创建 RSI 容器
            const rsiContainer = document.createElement('div');
            rsiContainer.style.width = '100%';
            rsiContainer.style.height = '150px';
            rsiContainer.style.position = 'relative';
            rsiContainer.style.marginTop = '10px';
            
            // 添加 RSI 容器到主容器
            container.appendChild(rsiContainer);
            
            // 调整体积容器的高度
            volumeContainer.style.height = 'calc(20% - 5px)';
            chartContainer.style.height = 'calc(60% - 5px)';
            
            // 更新比例标签
            ratioLabel.textContent = '60/20/20';
            
            // 创建 RSI 图表
            rsiChart = LightweightCharts.createChart(rsiContainer, {
                ...commonChartOptions,
                height: 150,
                rightPriceScale: {
                    ...commonChartOptions.rightPriceScale,
                    scaleMargins: {
                        top: 0.1,
                        bottom: 0.1,
                    },
                    visible: true,
                },
                timeScale: {
                    ...commonChartOptions.timeScale,
                    visible: true,
                },
                watermark: {
                    ...commonChartOptions.watermark,
                    visible: false,
                },
                // 修改RSI图表的鼠标滚轮和拖动行为
                handleScale: {
                    // 允许通过鼠标拖动改变时间范围，但不改变价格范围
                    axisPressedMouseMove: {
                        time: false,
                        price: false,
                    },
                    mouseWheel: true, // 在RSI图表上启用鼠标滚轮缩放时间范围
                    pinch: true,
                },
            });
            
            // 添加 RSI 线
            const rsiSeries = rsiChart.addLineSeries({
                color: '#F5BD78',
                lineWidth: 2,
                title: 'RSI(14)',
                priceFormat: {
                    type: 'custom',
                    formatter: (price) => price.toFixed(2),
                },
            });
            
            // 添加 RSI 超买超卖线
            const rsiOverSoldLine = rsiChart.addLineSeries({
                color: 'rgba(255, 0, 0, 0.5)',
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dashed,
                title: '超卖区域',
                priceFormat: {
                    type: 'custom',
                    formatter: () => '',
                },
            });
            
            const rsiOverBoughtLine = rsiChart.addLineSeries({
                color: 'rgba(0, 255, 0, 0.5)',
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dashed,
                title: '超买区域',
                priceFormat: {
                    type: 'custom',
                    formatter: () => '',
                },
            });
            
            // 设置 RSI 数据
            rsiSeries.setData(chartData.rsi);
            
            // 设置超买超卖线
            const rsiOverSoldData = chartData.rsi.map(item => ({
                time: item.time,
                value: 30,
            }));
            
            const rsiOverBoughtData = chartData.rsi.map(item => ({
                time: item.time,
                value: 70,
            }));
            
            rsiOverSoldLine.setData(rsiOverSoldData);
            rsiOverBoughtLine.setData(rsiOverBoughtData);
            
            // 为 rsiChart 与其他所有图表建立同步
            allCharts.forEach(chart => {
                if (chart !== rsiChart) {
                    syncTimeScale(rsiChart, [chart]);
                    syncTimeScale(chart, [rsiChart]);
                    syncCrosshair(rsiChart, [chart]);
                    syncCrosshair(chart, [rsiChart]);
                }
            });
            
            // 创建 RSI 图表图例
            createLegend(rsiChart, rsiContainer, [
                { label: 'RSI(14)', color: '#F5BD78' },
                { label: '超买(70)', color: 'rgba(0, 255, 0, 0.5)' },
                { label: '超卖(30)', color: 'rgba(255, 0, 0, 0.5)' },
            ]);
            
            // 调整分隔线拖动逻辑
            // 使拖动同时影响价格和成交量图表
            dividerContainer.addEventListener('mousedown', function(e) {
                isDragging = true;
                startY = e.clientY;
                initialChartHeight = chartContainer.offsetHeight;
                containerHeight = container.offsetHeight - dividerContainer.offsetHeight - rsiContainer.offsetHeight;
                
                document.body.style.cursor = 'ns-resize';
                e.preventDefault();
            });
            
            document.addEventListener('mousemove', function(e) {
                if (isDragging) {
                    const delta = e.clientY - startY;
                    const newChartHeight = Math.max(50, Math.min(containerHeight - 50, initialChartHeight + delta));
                    
                    chartRatio = newChartHeight / containerHeight;
                    const volumeRatio = 1 - chartRatio;
                    
                    chartContainer.style.height = `calc(${Math.round(chartRatio * 100)}% - 5px)`;
                    volumeContainer.style.height = `calc(${Math.round(volumeRatio * 100)}% - 5px)`;
                    
                    ratioLabel.textContent = `${Math.round(chartRatio * 100)}/${Math.round(volumeRatio * 100)}`;
                    
                    // 重新调整图表
                    if (priceChart && volumeChart && rsiChart) {
                        priceChart.resize(chartContainer.clientWidth, chartContainer.clientHeight);
                        volumeChart.resize(volumeContainer.clientWidth, volumeContainer.clientHeight);
                        rsiChart.resize(rsiContainer.clientWidth, rsiContainer.clientHeight);
                    }
                    
                    e.preventDefault();
                }
            });
        }
        
        // 添加 MACD 指标（如果有数据，直接在成交量图表下方添加）
        if (showMacd && chartData.macd && chartData.macd.length > 0 && (!rsiChart)) { // 确保 rsiChart 已检查
            // 创建 MACD 容器
            const macdContainer = document.createElement('div');
            macdContainer.style.width = '100%';
            macdContainer.style.height = '150px';
            macdContainer.style.position = 'relative';
            macdContainer.style.marginTop = '10px';
            
            // 添加 MACD 容器到主容器
            container.appendChild(macdContainer);
            
            // 调整体积容器的高度
            volumeContainer.style.height = 'calc(20% - 5px)';
            chartContainer.style.height = 'calc(60% - 5px)';
            
            // 更新比例标签
            ratioLabel.textContent = '60/20/20';
            
            // 创建 MACD 图表
            macdChart = LightweightCharts.createChart(macdContainer, {
                ...commonChartOptions,
                height: 150,
                rightPriceScale: {
                    ...commonChartOptions.rightPriceScale,
                    scaleMargins: {
                        top: 0.1,
                        bottom: 0.1,
                    },
                    visible: true,
                },
                timeScale: {
                    ...commonChartOptions.timeScale,
                    visible: true,
                },
                watermark: {
                    ...commonChartOptions.watermark,
                    visible: false,
                },
                // 修改MACD图表的鼠标滚轮和拖动行为
                handleScale: {
                    // 允许通过鼠标拖动改变时间范围，但不改变价格范围
                    axisPressedMouseMove: {
                        time: false,
                        price: false,
                    },
                    mouseWheel: true, // 在MACD图表上启用鼠标滚轮缩放时间范围
                    pinch: true,
                },
            });
            
            // 添加 MACD 线
            const macdSeries = macdChart.addLineSeries({
                color: '#2196F3',
                lineWidth: 2,
                title: 'MACD',
                priceFormat: {
                    type: 'custom',
                    formatter: (price) => price.toFixed(4),
                },
            });
            
            // 添加信号线
            const signalSeries = macdChart.addLineSeries({
                color: '#FF9800',
                lineWidth: 1,
                title: 'Signal',
                priceFormat: {
                    type: 'custom',
                    formatter: (price) => price.toFixed(4),
                },
            });
            
            // 添加柱状图
            const histogramSeries = macdChart.addHistogramSeries({
                color: '#26a69a',
                priceFormat: {
                    type: 'custom',
                    formatter: (price) => price.toFixed(4),
                },
                title: 'Histogram',
            });
            
            // 设置 MACD 数据
            macdSeries.setData(chartData.macd);
            signalSeries.setData(chartData.signal);
            
            // 设置柱状图数据，根据正负值设置颜色
            const histogramData = chartData.histogram.map(item => ({
                time: item.time,
                value: item.value,
                color: item.value >= 0 ? '#26a69a' : '#ef5350',
            }));
            
            histogramSeries.setData(histogramData);
            
            // 为 macdChart 与其他所有图表建立同步
            allCharts.forEach(chart => {
                if (chart !== macdChart) {
                    syncTimeScale(macdChart, [chart]);
                    syncTimeScale(chart, [macdChart]);
                    syncCrosshair(macdChart, [chart]);
                    syncCrosshair(chart, [macdChart]);
                }
            });
            
            // 创建 MACD 图表图例
            createLegend(macdChart, macdContainer, [
                { label: 'MACD', color: '#2196F3' },
                { label: 'Signal', color: '#FF9800' },
                { label: '柱状图', color: '#26a69a' },
            ]);
        }
        
        // 创建交易标记
        if (showTrades && tradesData && tradesData.length > 0) {
            try {
                // 创建一个数组来存储所有标记
                const markers = [];
                
                // 将交易标记添加到图表
                tradesData.forEach(trade => {
                    if (!trade.time || !trade.price) return;
                    
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
                    candlestickSeries.setMarkers(markers);
                }
                
                // 添加鼠标悬停事件以显示交易详情
                let activeTooltip = null; // 当前活跃的提示框
                let isTooltipPinned = false; // 提示框是否固定

                chartContainer.addEventListener('mousemove', (e) => {
                    if (isTooltipPinned) return; // 如果提示框已固定，不进行处理
                    
                    const rect = chartContainer.getBoundingClientRect();
                    const x = e.clientX - rect.left;
                    const y = e.clientY - rect.top;
                    
                    // 获取光标下的点
                    const point = {x, y};
                    const coordsResponse = candlestickSeries.priceToCoordinate(point.y);
                    if (!coordsResponse) return;
                    
                    // 获取时间点
                    const timePoint = priceChart.timeScale().coordinateToTime(point.x);
                    if (!timePoint) return;
                    
                    // 查找匹配的交易记录
                    const matchingTrade = tradesData.find(trade => {
                        // 增大时间和价格的容差，使得更容易触发交易详情
                        const timeTolerance = 100000; // 增大时间容差（毫秒）
                        const priceTolerance = 20; // 增大价格容差（像素）
                        
                        // 首先检查时间是否接近
                        if (Math.abs(trade.time - timePoint) > timeTolerance) {
                            return false;
                        }
                        
                        // 计算交易价格到鼠标位置的距离
                        const tradeY = candlestickSeries.priceToCoordinate(trade.price);
                        if (tradeY === null) {
                            return false;
                        }

                        // 计算距离，下单类型决定检查方向
                        if (trade.side === 'buy') {
                            // 买入标记在下方，鼠标需要在marker附近或下方
                            return Math.abs(tradeY - point.y) < priceTolerance && 
                                   (point.y >= tradeY || Math.abs(point.y - tradeY) < 10);
                        } else {
                            // 卖出标记在上方，鼠标需要在marker附近或上方
                            return Math.abs(tradeY - point.y) < priceTolerance && 
                                   (point.y <= tradeY || Math.abs(point.y - tradeY) < 10);
                        }
                    });
                    
                    if (matchingTrade) {
                        showTradeTooltip(e, matchingTrade, false);
                    } else if (document.getElementById('trade-tooltip') && !isTooltipPinned) {
                        document.getElementById('trade-tooltip').style.display = 'none';
                        activeTooltip = null;
                    }
                });

                // 添加点击事件，固定或取消固定提示框
                chartContainer.addEventListener('click', (e) => {
                    const rect = chartContainer.getBoundingClientRect();
                    const x = e.clientX - rect.left;
                    const y = e.clientY - rect.top;
                    
                    // 获取点击位置的信息
                    const point = {x, y};
                    const timePoint = priceChart.timeScale().coordinateToTime(point.x);
                    if (!timePoint) return;
                    
                    // 查找匹配的交易记录
                    const matchingTrade = tradesData.find(trade => {
                        // 与悬停相同的匹配逻辑
                        const timeTolerance = 100000;
                        const priceTolerance = 20;
                        
                        if (Math.abs(trade.time - timePoint) > timeTolerance) {
                            return false;
                        }
                        
                        const tradeY = candlestickSeries.priceToCoordinate(trade.price);
                        if (tradeY === null) {
                            return false;
                        }

                        if (trade.side === 'buy') {
                            return Math.abs(tradeY - point.y) < priceTolerance && 
                                   (point.y >= tradeY || Math.abs(point.y - tradeY) < 10);
                        } else {
                            return Math.abs(tradeY - point.y) < priceTolerance && 
                                   (point.y <= tradeY || Math.abs(point.y - tradeY) < 10);
                        }
                    });
                    
                    if (matchingTrade) {
                        // 如果点击了交易标记
                        if (isTooltipPinned && activeTooltip && activeTooltip.trade === matchingTrade) {
                            // 如果点击了已经固定的标记，取消固定
                            isTooltipPinned = false;
                            document.getElementById('trade-tooltip').style.display = 'none';
                            activeTooltip = null;
                        } else {
                            // 显示并固定提示框
                            showTradeTooltip(e, matchingTrade, true);
                            isTooltipPinned = true;
                        }
                    } else if (isTooltipPinned) {
                        // 点击了其他地方，取消固定
                        isTooltipPinned = false;
                        document.getElementById('trade-tooltip').style.display = 'none';
                        activeTooltip = null;
                    }
                });
                
                // 创建显示交易提示框的函数
                function showTradeTooltip(e, trade, isPinned) {
                    // 创建或更新交易提示框
                    let tooltip = document.getElementById('trade-tooltip');
                    if (!tooltip) {
                        tooltip = document.createElement('div');
                        tooltip.id = 'trade-tooltip';
                        document.body.appendChild(tooltip);
                    }
                    
                    // 保存当前活跃的提示框信息
                    activeTooltip = { tooltip, trade };
                    
                    // 设置提示框样式
                    Object.assign(tooltip.style, {
                        position: 'absolute',
                        left: `${e.clientX + 10}px`,
                        top: `${e.clientY + 10}px`,
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        color: '#fff',
                        padding: '8px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        zIndex: 1000,
                        display: 'block',
                        pointerEvents: 'none',
                        whiteSpace: 'nowrap',
                        boxShadow: isPinned ? '0 0 8px rgba(255,255,255,0.5)' : '0 2px 5px rgba(0,0,0,0.3)',
                        border: isPinned ? '1px solid #4CAF50' : 'none'
                    });
                    
                    // 格式化日期时间
                    const date = new Date(trade.time);
                    const formattedDate = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
                    
                    // 设置提示框内容
                    tooltip.innerHTML = `
                        <div style="border-bottom: 1px solid #555; padding-bottom: 4px; margin-bottom: 4px;">
                            <strong style="color: ${isPinned ? '#4CAF50' : '#FFF'}">
                                交易详情 ${isPinned ? '(已固定)' : ''}
                            </strong>
                            ${isPinned ? '<div style="font-size: 10px; color: #AAA">点击标记或其他地方关闭</div>' : ''}
                        </div>
                        <div><strong>时间:</strong> ${formattedDate}</div>
                        <div><strong>方向:</strong> <span style="color:${trade.side === 'buy' ? '#26a69a' : '#ef5350'}">${trade.side === 'buy' ? '买入' : '卖出'}</span></div>
                        <div><strong>开仓价格:</strong> ${trade.price}</div>
                        <div><strong>平仓价格:</strong> ${trade.closingPrice || '未平仓'}</div>
                        <div><strong>数量:</strong> ${trade.amount}</div>
                        <div><strong>价值:</strong> ${trade.cost.toFixed(2)} USDT</div>
                        <div><strong>保证金:</strong> ${(trade.cost / 10).toFixed(2)} USDT</div>
                        <div><strong>盈亏:</strong> <span style="color:${trade.pnl > 0 ? '#26a69a' : (trade.pnl < 0 ? '#ef5350' : '#ffffff')}">${trade.pnl ? trade.pnl.toFixed(2) + ' USDT' : '未知'}</span></div>
                        <div><strong>杠杆:</strong> ${trade.leverage || '10'}x</div>
                    `;
                    
                    // 当移出图表时删除提示框（仅对非固定状态）
                    if (!isPinned) {
                        chartContainer.addEventListener('mouseleave', () => {
                            if (tooltip && !isTooltipPinned) tooltip.style.display = 'none';
                        }, { once: true });
                    }
                }
            } catch (error) {
                console.error('解析交易数据时出错:', error);
            }
        }
        
        // 添加十字线和价格标签
        const container_rect = container.getBoundingClientRect();
        const toolTipWidth = 150;
        const toolTipHeight = 120;
        const toolTipMargin = 15;
        
        // 创建十字线工具提示元素
        const toolTip = document.createElement('div');
        toolTip.className = 'floating-tooltip';
        toolTip.style.display = 'none';
        toolTip.style.position = 'absolute';
        toolTip.style.zIndex = '1000';
        toolTip.style.padding = '8px';
        toolTip.style.backgroundColor = 'rgba(33, 56, 77, 0.9)';
        toolTip.style.color = 'white';
        toolTip.style.fontSize = '12px';
        toolTip.style.borderRadius = '4px';
        toolTip.style.boxShadow = '0 2px 5px rgba(0, 0, 0, 0.5)';
        toolTip.style.pointerEvents = 'none';
        container.appendChild(toolTip);
        
        // 监听十字线移动
        priceChart.subscribeCrosshairMove((param) => {
            if (param.point === undefined || !param.time || param.point.x < 0 || param.point.x > container_rect.width || param.point.y < 0 || param.point.y > container_rect.height) {
                toolTip.style.display = 'none';
                return;
            }
            
            const dateStr = new Date(param.time * 1000).toLocaleString();
            toolTip.style.display = 'block';
            
            const price = param.seriesPrices.get(candlestickSeries);
            const ema = ema20Series ? param.seriesPrices.get(ema20Series) : null;
            
            // 获取体积数据
            let volume = null;
            volumeChart.subscribeCrosshairMove((volumeParam) => {
                if (volumeParam.time === param.time) {
                    volume = volumeParam.seriesPrices.get(volumeSeries);
                }
            });
            
            let content = `<div style="margin-bottom:5px;font-weight:bold;border-bottom:1px solid #758696;">时间: ${dateStr}</div>`;
            
            if (price) {
                content += `
                    <div style="display:flex;justify-content:space-between;">
                        <span>开盘:</span><span style="color:${price.open <= price.close ? '#26a69a' : '#ef5350'}">${price.open.toFixed(4)}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;">
                        <span>最高:</span><span style="color:#26a69a">${price.high.toFixed(4)}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;">
                        <span>最低:</span><span style="color:#ef5350">${price.low.toFixed(4)}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;">
                        <span>收盘:</span><span style="color:${price.open <= price.close ? '#26a69a' : '#ef5350'}">${price.close.toFixed(4)}</span>
                    </div>
                `;
            }
            
            if (volume !== null) {
                content += `<div style="display:flex;justify-content:space-between;">
                    <span>成交量:</span><span>${volume.toFixed(2)}</span>
                </div>`;
            }
            
            if (ema) {
                content += `<div style="display:flex;justify-content:space-between;">
                    <span>EMA20:</span><span style="color:#f48fb1">${ema.toFixed(4)}</span>
                </div>`;
            }
            
            toolTip.innerHTML = content;
            
            // A函数：更新交互信息到Dash
            try {
                const interactionData = {
                    time: dateStr,
                    price: price ? price.close : null,
                    open: price ? price.open : null,
                    high: price ? price.high : null,
                    low: price ? price.low : null,
                    close: price ? price.close : null,
                    volume: volume || null,
                    ema20: ema || null,
                };
                
                // 更新交互元素
                const interactionElement = document.getElementById('chart-interaction');
                if (interactionElement) {
                    interactionElement.innerHTML = JSON.stringify(interactionData);
                    
                    // 触发变更事件
                    const event = new Event('change');
                    interactionElement.dispatchEvent(event);
                }
            } catch (e) {
                console.error('更新交互数据失败:', e);
            }
            
            // 定位工具提示
            const y = param.point.y;
            const left = param.point.x + toolTipMargin;
            const right = container_rect.width - left - toolTipWidth;
            const top = y + toolTipMargin;
            const bottom = container_rect.height - top - toolTipHeight;
            
            if (right < 0) {
                toolTip.style.left = 'auto';
                toolTip.style.right = '5px';
            } else {
                toolTip.style.right = 'auto';
                toolTip.style.left = `${left}px`;
            }
            
            if (bottom < 0) {
                toolTip.style.top = 'auto';
                toolTip.style.bottom = '5px';
            } else {
                toolTip.style.bottom = 'auto';
                toolTip.style.top = `${top}px`;
            }
        });
        
        // 调整图表大小
        const resizeChart = () => {
            allCharts.forEach((chart, index) => {
                let chartElement;
                if (chart === priceChart) chartElement = chartContainer;
                else if (chart === volumeChart) chartElement = volumeContainer;
                else if (chart === rsiChart) chartElement = rsiContainer; // 需要确保 rsiContainer 可访问
                else if (chart === macdChart) chartElement = macdContainer; // 需要确保 macdContainer 可访问
                
                if (chartElement) {
                    chart.resize(chartElement.clientWidth, chartElement.clientHeight);
                }
            });
        };
        
        // 监听窗口大小变化
        window.addEventListener('resize', resizeChart);
        
        // 初始调整大小
        resizeChart();
        
        // 使用已经在文件顶部定义的createLegend
        
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
        
        // 为所有图表添加交互（现在 allCharts 包含了所有活动图表）
        allCharts.forEach(chart => {
            let containerEl;
            let isMain = false;
            if (chart === priceChart) { containerEl = chartContainer; isMain = true; }
            else if (chart === volumeChart) { containerEl = volumeContainer; }
            else if (chart === rsiChart) { containerEl = rsiContainer; } // rsiContainer 需要在作用域内
            else if (chart === macdChart) { containerEl = macdContainer; } // macdContainer 需要在作用域内
            
            if (containerEl) {
                addChartInteractions(chart, containerEl, isMain);
            }
        });
        
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