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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import {
  formatCurrency,
  formatPercent,
  formatDate,
  getPnlColor,
} from "@/lib/utils";
import {
  Plus,
  ExternalLink,
  Trash2,
  X,
  RefreshCcw,
} from "lucide-react";

interface Position {
  id: number;
  ticker: string;
  asset_type: string;
  quantity: number;
  buy_price: number;
  purchase_date: string;
  current_price: number;
  cost_basis: number;
  current_value: number;
  pnl: number;
  pnl_percent: number;
  status: string;
}

const ASSET_TYPES = [
  { value: "stock", label: "Stock" },
  { value: "etf", label: "ETF" },
  { value: "crypto", label: "Crypto" },
  { value: "bond", label: "Bond" },
  { value: "mutual_fund", label: "Mutual Fund" },
];

export default function JournalPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [ticker, setTicker] = useState("");
  const [assetType, setAssetType] = useState("stock");
  const [quantity, setQuantity] = useState("");
  const [buyPrice, setBuyPrice] = useState("");
  const [purchaseDate, setPurchaseDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      setLoading(true);
      const [positionsData, historyData] = await Promise.all([
        api.getPositions("active").catch(() => []),
        api.getTradeHistory().catch(() => []),
      ]);
      setPositions(positionsData);
      setHistory(historyData);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load data");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!ticker || !quantity || !buyPrice) {
      setError("Please fill in all required fields");
      return;
    }

    try {
      setSubmitting(true);
      await api.confirmTrade({
        ticker: ticker.toUpperCase(),
        asset_type: assetType,
        quantity: parseFloat(quantity),
        buy_price: parseFloat(buyPrice),
        purchase_date: purchaseDate,
        notes: notes || undefined,
      });

      // Reset form
      setTicker("");
      setQuantity("");
      setBuyPrice("");
      setNotes("");
      setShowForm(false);

      // Reload data
      await loadData();
    } catch (err: any) {
      setError(err.message || "Failed to log trade");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Are you sure you want to delete this position?")) return;

    try {
      await api.deletePosition(id);
      await loadData();
    } catch (err: any) {
      setError(err.message || "Failed to delete position");
    }
  }

  async function handleClose(id: number) {
    const sellPrice = prompt("Enter sell price:");
    if (!sellPrice) return;

    try {
      await api.closePosition(id, parseFloat(sellPrice));
      await loadData();
    } catch (err: any) {
      setError(err.message || "Failed to close position");
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Trade Journal</h1>
          <p className="text-muted-foreground">
            Track and manage your confirmed trades
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadData}>
            <RefreshCcw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button onClick={() => setShowForm(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Log Trade
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-destructive">
          {error}
          <button onClick={() => setError(null)} className="ml-4">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* New Trade Form */}
      {showForm && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Log New Trade</CardTitle>
              <Button variant="ghost" size="sm" onClick={() => setShowForm(false)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            <CardDescription>
              Record a trade you&apos;ve executed on Robinhood
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="ticker">Ticker Symbol *</Label>
                  <Input
                    id="ticker"
                    value={ticker}
                    onChange={(e) => setTicker(e.target.value.toUpperCase())}
                    placeholder="AAPL"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="assetType">Asset Type *</Label>
                  <Select value={assetType} onValueChange={setAssetType}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ASSET_TYPES.map((type) => (
                        <SelectItem key={type.value} value={type.value}>
                          {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="quantity">Quantity *</Label>
                  <Input
                    id="quantity"
                    type="number"
                    step="any"
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    placeholder="10"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="buyPrice">Buy Price *</Label>
                  <Input
                    id="buyPrice"
                    type="number"
                    step="0.01"
                    value={buyPrice}
                    onChange={(e) => setBuyPrice(e.target.value)}
                    placeholder="150.00"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="purchaseDate">Purchase Date *</Label>
                  <Input
                    id="purchaseDate"
                    type="date"
                    value={purchaseDate}
                    onChange={(e) => setPurchaseDate(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="notes">Notes</Label>
                  <Input
                    id="notes"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Optional notes"
                  />
                </div>
              </div>
              <Button type="submit" disabled={submitting}>
                {submitting ? "Logging..." : "Log Trade"}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Positions */}
      <Tabs defaultValue="active">
        <TabsList>
          <TabsTrigger value="active">Active Positions ({positions.length})</TabsTrigger>
          <TabsTrigger value="history">Trade History ({history.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="active" className="mt-4">
          <Card>
            <CardContent className="p-0">
              {positions.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  No active positions. Log a trade to get started.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b bg-muted/50">
                        <th className="px-4 py-3 text-left text-sm font-medium">Ticker</th>
                        <th className="px-4 py-3 text-left text-sm font-medium">Type</th>
                        <th className="px-4 py-3 text-right text-sm font-medium">Qty</th>
                        <th className="px-4 py-3 text-right text-sm font-medium">Buy Price</th>
                        <th className="px-4 py-3 text-right text-sm font-medium">Current</th>
                        <th className="px-4 py-3 text-right text-sm font-medium">Cost Basis</th>
                        <th className="px-4 py-3 text-right text-sm font-medium">Value</th>
                        <th className="px-4 py-3 text-right text-sm font-medium">P&L</th>
                        <th className="px-4 py-3 text-right text-sm font-medium">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {positions.map((pos) => (
                        <tr key={pos.id} className="border-b hover:bg-muted/50">
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{pos.ticker}</span>
                              <a
                                href={`https://robinhood.com/stocks/${pos.ticker}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-muted-foreground hover:text-primary"
                              >
                                <ExternalLink className="h-3 w-3" />
                              </a>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm capitalize">
                            {pos.asset_type}
                          </td>
                          <td className="px-4 py-3 text-right text-sm">
                            {pos.quantity}
                          </td>
                          <td className="px-4 py-3 text-right text-sm">
                            {formatCurrency(pos.buy_price)}
                          </td>
                          <td className="px-4 py-3 text-right text-sm">
                            {formatCurrency(pos.current_price)}
                          </td>
                          <td className="px-4 py-3 text-right text-sm">
                            {formatCurrency(pos.cost_basis)}
                          </td>
                          <td className="px-4 py-3 text-right text-sm">
                            {formatCurrency(pos.current_value)}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <div className={getPnlColor(pos.pnl)}>
                              <div className="text-sm font-medium">
                                {formatCurrency(pos.pnl)}
                              </div>
                              <div className="text-xs">
                                {formatPercent(pos.pnl_percent)}
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <div className="flex justify-end gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleClose(pos.id)}
                              >
                                Close
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDelete(pos.id)}
                              >
                                <Trash2 className="h-4 w-4 text-destructive" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history" className="mt-4">
          <Card>
            <CardContent className="p-0">
              {history.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  No closed trades yet.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b bg-muted/50">
                        <th className="px-4 py-3 text-left text-sm font-medium">Ticker</th>
                        <th className="px-4 py-3 text-left text-sm font-medium">Type</th>
                        <th className="px-4 py-3 text-right text-sm font-medium">Qty</th>
                        <th className="px-4 py-3 text-right text-sm font-medium">Buy</th>
                        <th className="px-4 py-3 text-right text-sm font-medium">Sell</th>
                        <th className="px-4 py-3 text-right text-sm font-medium">P&L</th>
                        <th className="px-4 py-3 text-left text-sm font-medium">Dates</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.map((trade) => (
                        <tr key={trade.id} className="border-b hover:bg-muted/50">
                          <td className="px-4 py-3 font-medium">{trade.ticker}</td>
                          <td className="px-4 py-3 text-sm capitalize">
                            {trade.asset_type}
                          </td>
                          <td className="px-4 py-3 text-right text-sm">
                            {trade.quantity}
                          </td>
                          <td className="px-4 py-3 text-right text-sm">
                            {formatCurrency(trade.buy_price)}
                          </td>
                          <td className="px-4 py-3 text-right text-sm">
                            {formatCurrency(trade.sell_price)}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <div className={getPnlColor(trade.pnl)}>
                              <div className="text-sm font-medium">
                                {formatCurrency(trade.pnl)}
                              </div>
                              <div className="text-xs">
                                {formatPercent(trade.pnl_percent)}
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm text-muted-foreground">
                            {formatDate(trade.purchase_date)} →{" "}
                            {formatDate(trade.sell_date)}
                            <div className="text-xs">
                              {trade.holding_period_days} days
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
