"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EquityChart } from "@/components/charts/equity-chart";
import { AllocationChart } from "@/components/charts/allocation-chart";
import { api } from "@/lib/api";
import {
  formatCurrency,
  formatPercent,
  getPnlColor,
} from "@/lib/utils";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  PieChart,
  Activity,
  RefreshCcw,
} from "lucide-react";

interface PortfolioSummary {
  total_value: number;
  total_cost_basis: number;
  total_pnl: number;
  pnl_percent: number;
  positions_count: number;
  sharpe_ratio?: number;
  win_rate?: number;
}

interface PerformanceData {
  timestamp: string;
  total_value: number;
  total_pnl: number;
}

export default function DashboardPage() {
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [performance, setPerformance] = useState<PerformanceData[]>([]);
  const [allocation, setAllocation] = useState<any>(null);
  const [period, setPeriod] = useState("1m");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, [period]);

  async function loadData() {
    try {
      setLoading(true);
      const [portfolioData, performanceData, allocationData] = await Promise.all([
        api.getPortfolioSummary().catch(() => null),
        api.getPerformance(period).catch(() => ({ data: [] })),
        api.getAllocation().catch(() => null),
      ]);

      setPortfolio(portfolioData);
      setPerformance(performanceData?.data || []);
      setAllocation(allocationData);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  }

  const chartData = performance.map((p) => ({
    date: p.timestamp,
    value: p.total_value,
  }));

  const allocationData = allocation?.by_asset_type
    ? Object.entries(allocation.by_asset_type).map(([name, data]: [string, any]) => ({
        name: name.toUpperCase(),
        value: data.value,
        percent: data.percent,
      }))
    : [];

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">
            Your portfolio overview and performance
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadData}>
            <RefreshCcw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Link href="/research">
            <Button>Generate Research</Button>
          </Link>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-destructive">
          {error}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Value</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(portfolio?.total_value || 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              Cost basis: {formatCurrency(portfolio?.total_cost_basis || 0)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total P&L</CardTitle>
            {(portfolio?.total_pnl || 0) >= 0 ? (
              <TrendingUp className="h-4 w-4 text-green-600" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-600" />
            )}
          </CardHeader>
          <CardContent>
            <div
              className={`text-2xl font-bold ${getPnlColor(
                portfolio?.total_pnl || 0
              )}`}
            >
              {formatCurrency(portfolio?.total_pnl || 0)}
            </div>
            <p
              className={`text-xs ${getPnlColor(portfolio?.pnl_percent || 0)}`}
            >
              {formatPercent(portfolio?.pnl_percent || 0)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Positions</CardTitle>
            <PieChart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {portfolio?.positions_count || 0}
            </div>
            <p className="text-xs text-muted-foreground">Active positions</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {((portfolio?.win_rate || 0) * 100).toFixed(1)}%
            </div>
            <p className="text-xs text-muted-foreground">
              Sharpe: {portfolio?.sharpe_ratio?.toFixed(2) || "N/A"}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Portfolio Performance</CardTitle>
            <CardDescription>Value over time</CardDescription>
            <Tabs value={period} onValueChange={setPeriod}>
              <TabsList>
                <TabsTrigger value="1w">1W</TabsTrigger>
                <TabsTrigger value="1m">1M</TabsTrigger>
                <TabsTrigger value="3m">3M</TabsTrigger>
                <TabsTrigger value="1y">1Y</TabsTrigger>
                <TabsTrigger value="max">Max</TabsTrigger>
              </TabsList>
            </Tabs>
          </CardHeader>
          <CardContent>
            <EquityChart data={chartData} height={300} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Asset Allocation</CardTitle>
            <CardDescription>Portfolio breakdown by asset type</CardDescription>
          </CardHeader>
          <CardContent>
            <AllocationChart data={allocationData} height={300} />
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent className="flex gap-4">
          <Link href="/research">
            <Button>
              <Activity className="mr-2 h-4 w-4" />
              Generate Research
            </Button>
          </Link>
          <Link href="/journal">
            <Button variant="outline">
              <DollarSign className="mr-2 h-4 w-4" />
              Log Trade
            </Button>
          </Link>
          <Button variant="outline" onClick={() => api.createSnapshot()}>
            <RefreshCcw className="mr-2 h-4 w-4" />
            Create Snapshot
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
