/**
 * API client for the trading research backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface ApiError {
  detail: string;
}

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem("token", token);
    } else {
      localStorage.removeItem("token");
    }
  }

  getToken(): string | null {
    if (this.token) return this.token;
    if (typeof window !== "undefined") {
      return localStorage.getItem("token");
    }
    return null;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken();
    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    };

    if (token) {
      (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: "An error occurred",
      }));
      throw new Error(error.detail);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  // Auth
  async login(username: string, password: string) {
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);

    const response = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: "Login failed",
      }));
      throw new Error(error.detail);
    }

    const data = await response.json();
    this.setToken(data.access_token);
    return data;
  }

  async register(username: string, email: string, password: string) {
    return this.request<{ id: number; username: string; email: string }>(
      "/api/auth/register",
      {
        method: "POST",
        body: JSON.stringify({ username, email, password }),
      }
    );
  }

  async getMe() {
    return this.request<{ id: number; username: string; email: string }>(
      "/api/auth/me"
    );
  }

  logout() {
    this.setToken(null);
  }

  // Research
  async generateResearch(params: {
    asset_classes: string[];
    budget: number;
    risk_preference: string;
    specific_tickers?: string[];
  }) {
    return this.request<any>("/api/research/generate-sync", {
      method: "POST",
      body: JSON.stringify(params),
    });
  }

  async getReports(limit = 20, offset = 0) {
    return this.request<any[]>(
      `/api/research/reports?limit=${limit}&offset=${offset}`
    );
  }

  async getReport(id: number) {
    return this.request<any>(`/api/research/reports/${id}`);
  }

  async deleteReport(id: number) {
    return this.request<void>(`/api/research/reports/${id}`, {
      method: "DELETE",
    });
  }

  async getStrategies() {
    return this.request<{ strategies: any[] }>("/api/research/strategies");
  }

  // Trades
  async confirmTrade(params: {
    ticker: string;
    asset_type: string;
    quantity: number;
    buy_price: number;
    purchase_date: string;
    report_id?: number;
    notes?: string;
  }) {
    return this.request<any>("/api/trades/confirm", {
      method: "POST",
      body: JSON.stringify(params),
    });
  }

  async getPositions(status = "active", assetType?: string) {
    let url = `/api/trades/positions?status=${status}`;
    if (assetType) url += `&asset_type=${assetType}`;
    return this.request<any[]>(url);
  }

  async getPosition(id: number) {
    return this.request<any>(`/api/trades/positions/${id}`);
  }

  async closePosition(id: number, sellPrice: number, sellDate?: string) {
    return this.request<any>(`/api/trades/positions/${id}/close`, {
      method: "PUT",
      body: JSON.stringify({
        sell_price: sellPrice,
        sell_date: sellDate,
      }),
    });
  }

  async deletePosition(id: number) {
    return this.request<void>(`/api/trades/positions/${id}`, {
      method: "DELETE",
    });
  }

  async getTradeHistory(limit = 50, offset = 0) {
    return this.request<any[]>(
      `/api/trades/history?limit=${limit}&offset=${offset}`
    );
  }

  async getTradeSummary() {
    return this.request<any>("/api/trades/summary");
  }

  // Analytics
  async getPortfolioSummary() {
    return this.request<any>("/api/analytics/portfolio");
  }

  async getAllocation() {
    return this.request<any>("/api/analytics/allocation");
  }

  async getPerformance(period = "1m") {
    return this.request<any>(`/api/analytics/performance?period=${period}`);
  }

  async createSnapshot() {
    return this.request<any>("/api/analytics/snapshot", { method: "POST" });
  }

  async getMetrics() {
    return this.request<any>("/api/analytics/metrics");
  }

  async getBenchmarkComparison(benchmark = "SPY", period = "1y") {
    return this.request<any>(
      `/api/analytics/benchmark?benchmark=${benchmark}&period=${period}`
    );
  }

  async getPositionsPerformance() {
    return this.request<any>("/api/analytics/positions/performance");
  }

  async getAssetTypeBreakdown() {
    return this.request<any>("/api/analytics/asset-type-breakdown");
  }

  // Data
  async getCurrentPrice(ticker: string) {
    return this.request<any>(`/api/analytics/data/price/${ticker}`);
  }

  async getHistoricalPrices(
    ticker: string,
    period = "1y",
    interval = "1d"
  ) {
    return this.request<any>(
      `/api/analytics/data/historical/${ticker}?period=${period}&interval=${interval}`
    );
  }
}

export const api = new ApiClient();
