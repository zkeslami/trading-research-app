"use client";

import { useState } from "react";
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
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { api } from "@/lib/api";
import {
  formatCurrency,
  formatPercent,
  getRiskColor,
} from "@/lib/utils";
import {
  FlaskConical,
  Loader2,
  TrendingUp,
  ExternalLink,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

interface Pick {
  rank: number;
  ticker: string;
  current_price: number;
  expected_1y_yield: number;
  confidence: number;
  risk_level: string;
  allocation_percent: number;
  allocation_amount: number;
  rationale: string;
}

interface ResearchResult {
  id: number;
  picks: Pick[];
  full_report: string;
}

const ASSET_CLASSES = [
  { id: "stocks", label: "Stocks" },
  { id: "etfs", label: "ETFs" },
  { id: "crypto", label: "Crypto" },
  { id: "bonds", label: "Bonds" },
  { id: "mutual_funds", label: "Mutual Funds" },
];

export default function ResearchPage() {
  const [selectedAssets, setSelectedAssets] = useState<string[]>(["stocks", "etfs"]);
  const [budget, setBudget] = useState(500);
  const [riskPreference, setRiskPreference] = useState("moderate");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ResearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedPick, setExpandedPick] = useState<number | null>(null);

  async function handleGenerate() {
    if (selectedAssets.length === 0) {
      setError("Please select at least one asset class");
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const data = await api.generateResearch({
        asset_classes: selectedAssets,
        budget,
        risk_preference: riskPreference,
      });

      setResult(data);
    } catch (err: any) {
      setError(err.message || "Failed to generate research");
    } finally {
      setLoading(false);
    }
  }

  function toggleAsset(assetId: string) {
    setSelectedAssets((prev) =>
      prev.includes(assetId)
        ? prev.filter((a) => a !== assetId)
        : [...prev, assetId]
    );
  }

  const riskValue =
    riskPreference === "conservative" ? 0 : riskPreference === "moderate" ? 50 : 100;

  function handleRiskChange(value: number[]) {
    if (value[0] < 33) setRiskPreference("conservative");
    else if (value[0] < 67) setRiskPreference("moderate");
    else setRiskPreference("aggressive");
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Research Lab</h1>
        <p className="text-muted-foreground">
          Generate AI-powered investment research and recommendations
        </p>
      </div>

      {/* Research Form */}
      <Card>
        <CardHeader>
          <CardTitle>Research Parameters</CardTitle>
          <CardDescription>
            Configure your research criteria and preferences
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Asset Classes */}
          <div className="space-y-3">
            <Label>Asset Classes</Label>
            <div className="flex flex-wrap gap-4">
              {ASSET_CLASSES.map((asset) => (
                <div key={asset.id} className="flex items-center space-x-2">
                  <Checkbox
                    id={asset.id}
                    checked={selectedAssets.includes(asset.id)}
                    onCheckedChange={() => toggleAsset(asset.id)}
                  />
                  <label
                    htmlFor={asset.id}
                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                  >
                    {asset.label}
                  </label>
                </div>
              ))}
            </div>
          </div>

          {/* Budget */}
          <div className="space-y-3">
            <Label htmlFor="budget">Investment Budget</Label>
            <div className="flex items-center gap-4">
              <Input
                id="budget"
                type="number"
                value={budget}
                onChange={(e) => setBudget(Number(e.target.value))}
                className="w-40"
              />
              <span className="text-muted-foreground">USD</span>
            </div>
          </div>

          {/* Risk Preference */}
          <div className="space-y-3">
            <Label>Risk Preference: {riskPreference.toUpperCase()}</Label>
            <Slider
              value={[riskValue]}
              onValueChange={handleRiskChange}
              max={100}
              step={1}
              className="w-full max-w-md"
            />
            <div className="flex justify-between text-xs text-muted-foreground max-w-md">
              <span>Conservative</span>
              <span>Moderate</span>
              <span>Aggressive</span>
            </div>
          </div>

          {error && (
            <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-destructive">
              {error}
            </div>
          )}

          <Button onClick={handleGenerate} disabled={loading} size="lg">
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Generating Research...
              </>
            ) : (
              <>
                <FlaskConical className="mr-2 h-4 w-4" />
                Generate Research
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Results */}
      {result && (
        <Card>
          <CardHeader>
            <CardTitle>Top 10 Investment Picks</CardTitle>
            <CardDescription>
              AI-recommended investments based on your criteria
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {result.picks.map((pick) => (
                <div
                  key={pick.ticker}
                  className="rounded-lg border p-4 hover:bg-accent/50 transition-colors"
                >
                  <div
                    className="flex items-center justify-between cursor-pointer"
                    onClick={() =>
                      setExpandedPick(
                        expandedPick === pick.rank ? null : pick.rank
                      )
                    }
                  >
                    <div className="flex items-center gap-4">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground font-bold">
                        {pick.rank}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-lg">{pick.ticker}</span>
                          <a
                            href={`https://robinhood.com/stocks/${pick.ticker}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-muted-foreground hover:text-primary"
                          >
                            <ExternalLink className="h-4 w-4" />
                          </a>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {formatCurrency(pick.current_price)} current price
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-8">
                      <div className="text-right">
                        <div className="flex items-center gap-1 text-green-600">
                          <TrendingUp className="h-4 w-4" />
                          <span className="font-semibold">
                            {formatPercent(pick.expected_1y_yield * 100, 1)}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          Expected 1Y Yield
                        </p>
                      </div>
                      <div className="text-right">
                        <div className="font-semibold">
                          {formatCurrency(pick.allocation_amount)}
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {pick.allocation_percent.toFixed(1)}% allocation
                        </p>
                      </div>
                      <div className="text-right">
                        <span
                          className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${getRiskColor(
                            pick.risk_level
                          )}`}
                        >
                          {pick.risk_level.toUpperCase()}
                        </span>
                        <p className="text-xs text-muted-foreground mt-1">
                          {(pick.confidence * 100).toFixed(0)}% confidence
                        </p>
                      </div>
                      {expandedPick === pick.rank ? (
                        <ChevronUp className="h-5 w-5" />
                      ) : (
                        <ChevronDown className="h-5 w-5" />
                      )}
                    </div>
                  </div>

                  {expandedPick === pick.rank && (
                    <div className="mt-4 pt-4 border-t">
                      <h4 className="font-semibold mb-2">Analysis Rationale</h4>
                      <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                        {pick.rationale}
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Full Report */}
      {result?.full_report && (
        <Card>
          <CardHeader>
            <CardTitle>Full Research Report</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="prose prose-sm max-w-none">
              <pre className="whitespace-pre-wrap text-sm bg-muted p-4 rounded-lg overflow-auto">
                {result.full_report}
              </pre>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
