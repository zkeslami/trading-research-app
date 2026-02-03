"use client";

import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EquityChart } from "@/components/charts/equity-chart";
import { AllocationChart } from "@/components/charts/allocation-chart";
import { api } from "@/lib/api";
import {
  formatCurrency,
  formatPercent,
  formatNumber,
  getPnlColor,
} from "@/lib/utils";
import {
  TrendingUp,
  TrendingDown,
  Activity,
  RefreshCcw,
  BarChart3,
} from "lucide-react";

interface Metrics {
  sharpe_ratio?: number;
  sortino_ratio?: number;
  max_drawdown?: number;
  volatility?: number;
  data_points?: number;
}

interface PositionPerformance {
  ticker: string;
  pnl: number;
  pnl_percent: number;
  current_value: number;
}

export default function AnalyticsPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [performance, setPerformance] = useState<any[]>([]);
  const [assetBreakdown, setAssetBreakdown] = useState<any>(null);
  const [positionsPerformance, setPositionsPerformance] = useState<any>(null);
  const [benchmark, setBenchmark] = useState<any>(null);
  const [period, setPeriod] = useState("3m");
  const [benchmarkSymbol, setBenchmarkSymbol] = useState("SPY");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, [period, benchmarkSymbol]);

  async function loadData() {
    try {
      setLoading(true);
      const [metricsData, performanceData, assetData, positionsData, benchmarkData] =
        await Promise.all([
          api.getMetrics().catch(() => null),
          api.getPerformance(period).catch(() => ({ data: [] })),
          api.getAssetTypeBreakdown().catch(() => null),
          api.getPositionsPerformance().catch(() => null),
          api.getBenchmarkComparison(benchmarkSymbol, period).catch(() => null),
        ]);

      setMetrics(metricsData);
      setPerformance(performanceData?.data || []);
      setAssetBreakdown(assetData);
      setPositionsPerformance(positionsData);
      setBenchmark(benchmarkData);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  }

  const chartData = performance.map((p: any) => ({
    date: p.timestamp,
    value: p.total_value,
  }));

  const assetAllocationData = assetBreakdown
    ? Object.entries(assetBreakdown).map(([name, data]: [string, any]) => ({
        name: name.toUpperCase(),
        value: data.total_value || 0,
        percent: data.percent_of_portfolio || 0,
      }))
    : [];

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Analytics</h1>
          <p className="text-muted-foreground">
            Portfolio performance metrics and analysis
          </p>
        </div>
        <div className="flex gap-2">
          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1m">1 Month</SelectItem>
              <SelectItem value="3m">3 Months</SelectItem>
              <SelectItem value="6m">6 Months</SelectItem>
              <SelectItem value="1y">1 Year</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={loadData}>
            <RefreshCcw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-destructive">
          {error}
        </div>
      )}

      {/* Key Metrics Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Sharpe Ratio</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {metrics?.sharpe_ratio?.toFixed(2) || "N/A"}
            </div>
            <p className="text-xs text-muted-foreground">
              Risk-adjusted return
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Sortino Ratio</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {metrics?.sortino_ratio?.toFixed(2) || "N/A"}
            </div>
            <p className="text-xs text-muted-foreground">
              Downside risk-adjusted
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Max Drawdown</CardTitle>
            <TrendingDown className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {metrics?.max_drawdown
                ? formatPercent(metrics.max_drawdown * 100)
                : "N/A"}
            </div>
            <p className="text-xs text-muted-foreground">
              Largest peak-to-trough decline
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Volatility</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {metrics?.volatility
                ? formatPercent(metrics.volatility * 100)
                : "N/A"}
            </div>
            <p className="text-xs text-muted-foreground">Annualized volatility</p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <Tabs defaultValue="performance">
        <TabsList>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="allocation">Allocation</TabsTrigger>
          <TabsTrigger value="positions">Positions</TabsTrigger>
        </TabsList>

        <TabsContent value="performance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Portfolio Performance</CardTitle>
              <CardDescription>
                Portfolio value over time ({period.toUpperCase()})
              </CardDescription>
            </CardHeader>
            <CardContent>
              <EquityChart data={chartData} height={400} />
            </CardContent>
          </Card>

          {/* Benchmark Comparison */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Benchmark Comparison</CardTitle>
                  <CardDescription>
                    Compare your portfolio to market benchmarks
                  </CardDescription>
                </div>
                <Select value={benchmarkSymbol} onValueChange={setBenchmarkSymbol}>
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="SPY">S&P 500 (SPY)</SelectItem>
                    <SelectItem value="QQQ">Nasdaq (QQQ)</SelectItem>
                    <SelectItem value="IWM">Russell 2000 (IWM)</SelectItem>
                    <SelectItem value="DIA">Dow Jones (DIA)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent>
              {benchmark ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="rounded-lg bg-muted p-4">
                      <p className="text-sm text-muted-foreground">Your Portfolio</p>
                      <p className="text-2xl font-bold">
                        {benchmark.portfolio_returns?.length > 0
                          ? formatPercent(
                              benchmark.portfolio_returns[
                                benchmark.portfolio_returns.length - 1
                              ]?.return * 100 || 0
                            )
                          : "N/A"}
                      </p>
                    </div>
                    <div className="rounded-lg bg-muted p-4">
                      <p className="text-sm text-muted-foreground">
                        {benchmarkSymbol}
                      </p>
                      <p className="text-2xl font-bold">
                        {benchmark.benchmark_returns?.length > 0
                          ? formatPercent(
                              benchmark.benchmark_returns[
                                benchmark.benchmark_returns.length - 1
                              ]?.return * 100 || 0
                            )
                          : "N/A"}
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center text-muted-foreground py-8">
                  No benchmark data available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="allocation">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Asset Type Breakdown</CardTitle>
                <CardDescription>
                  Portfolio allocation by asset class
                </CardDescription>
              </CardHeader>
              <CardContent>
                <AllocationChart data={assetAllocationData} height={300} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Allocation Details</CardTitle>
              </CardHeader>
              <CardContent>
                {assetBreakdown ? (
                  <div className="space-y-4">
                    {Object.entries(assetBreakdown).map(
                      ([type, data]: [string, any]) => (
                        <div
                          key={type}
                          className="flex items-center justify-between border-b pb-2"
                        >
                          <div>
                            <p className="font-medium capitalize">{type}</p>
                            <p className="text-sm text-muted-foreground">
                              {data.count} position(s)
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="font-medium">
                              {formatCurrency(data.total_value)}
                            </p>
                            <p
                              className={`text-sm ${getPnlColor(data.total_pnl)}`}
                            >
                              {formatCurrency(data.total_pnl)} (
                              {formatPercent(data.pnl_percent)})
                            </p>
                          </div>
                        </div>
                      )
                    )}
                  </div>
                ) : (
                  <div className="text-center text-muted-foreground py-8">
                    No allocation data available
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="positions">
          <Card>
            <CardHeader>
              <CardTitle>Position Performance</CardTitle>
              <CardDescription>
                Individual position P&L breakdown
              </CardDescription>
            </CardHeader>
            <CardContent>
              {positionsPerformance?.positions?.length > 0 ? (
                <div className="space-y-2">
                  {positionsPerformance.positions.map((pos: PositionPerformance) => (
                    <div
                      key={pos.ticker}
                      className="flex items-center justify-between rounded-lg border p-3"
                    >
                      <div>
                        <p className="font-medium">{pos.ticker}</p>
                        <p className="text-sm text-muted-foreground">
                          Value: {formatCurrency(pos.current_value)}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className={`font-medium ${getPnlColor(pos.pnl)}`}>
                          {formatCurrency(pos.pnl)}
                        </p>
                        <p className={`text-sm ${getPnlColor(pos.pnl_percent)}`}>
                          {formatPercent(pos.pnl_percent)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center text-muted-foreground py-8">
                  No position data available
                </div>
              )}
            </CardContent>
          </Card>

          {positionsPerformance?.summary && (
            <Card className="mt-4">
              <CardHeader>
                <CardTitle>Summary Statistics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Positions</p>
                    <p className="text-xl font-bold">
                      {positionsPerformance.summary.total_positions}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Winning</p>
                    <p className="text-xl font-bold text-green-600">
                      {positionsPerformance.summary.winning_positions}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Losing</p>
                    <p className="text-xl font-bold text-red-600">
                      {positionsPerformance.summary.losing_positions}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Total P&L</p>
                    <p
                      className={`text-xl font-bold ${getPnlColor(
                        positionsPerformance.summary.total_pnl
                      )}`}
                    >
                      {formatCurrency(positionsPerformance.summary.total_pnl)}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
