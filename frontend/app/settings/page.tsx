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
import { api } from "@/lib/api";
import { User, Key, Settings2, Info } from "lucide-react";

interface UserInfo {
  id: number;
  username: string;
  email: string;
  created_at: string;
}

export default function SettingsPage() {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadUser();
  }, []);

  async function loadUser() {
    try {
      const userData = await api.getMe();
      setUser(userData as UserInfo);
    } catch (err) {
      // Not logged in
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground">
          Manage your account and application preferences
        </p>
      </div>

      {/* User Profile */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <User className="h-5 w-5" />
            <CardTitle>User Profile</CardTitle>
          </div>
          <CardDescription>Your account information</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-muted-foreground">Loading...</p>
          ) : user ? (
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label>Username</Label>
                  <Input value={user.username} disabled />
                </div>
                <div>
                  <Label>Email</Label>
                  <Input value={user.email} disabled />
                </div>
              </div>
              <p className="text-sm text-muted-foreground">
                Account created: {new Date(user.created_at).toLocaleDateString()}
              </p>
            </div>
          ) : (
            <div className="text-center py-4">
              <p className="text-muted-foreground mb-4">
                You are not logged in. Please log in to view your profile.
              </p>
              <Button asChild>
                <a href="/login">Log In</a>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* API Configuration */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            <CardTitle>API Configuration</CardTitle>
          </div>
          <CardDescription>
            Configure API keys for enhanced functionality
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="rounded-lg bg-muted p-4">
              <h4 className="font-medium mb-2">LLM Provider</h4>
              <p className="text-sm text-muted-foreground mb-4">
                The application uses AI models for research analysis. Configure your
                preferred provider in the backend environment variables.
              </p>
              <ul className="text-sm space-y-1 text-muted-foreground">
                <li>• OpenAI: Set OPENAI_API_KEY</li>
                <li>• Anthropic: Set ANTHROPIC_API_KEY</li>
                <li>• Set LLM_PROVIDER to &quot;openai&quot; or &quot;anthropic&quot;</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Application Info */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Info className="h-5 w-5" />
            <CardTitle>About</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <h4 className="font-medium">Trading Research App</h4>
              <p className="text-sm text-muted-foreground">Version 1.0.0</p>
            </div>
            <div className="rounded-lg bg-muted p-4">
              <h4 className="font-medium mb-2">Important Notice</h4>
              <p className="text-sm text-muted-foreground">
                This application is for research and educational purposes only.
                It does not provide financial advice. All investments carry risk.
                Past performance does not guarantee future results. Please consult
                with a qualified financial advisor before making investment decisions.
              </p>
            </div>
            <div className="rounded-lg bg-yellow-50 border border-yellow-200 p-4">
              <h4 className="font-medium text-yellow-800 mb-2">No Direct Trading</h4>
              <p className="text-sm text-yellow-700">
                This application does NOT execute trades on your behalf. All
                recommendations are informational only. You must manually execute
                trades through Robinhood or your preferred broker.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Preferences */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Settings2 className="h-5 w-5" />
            <CardTitle>Preferences</CardTitle>
          </div>
          <CardDescription>Customize your experience</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Dark Mode</p>
                <p className="text-sm text-muted-foreground">
                  Toggle dark mode theme
                </p>
              </div>
              <Button variant="outline" disabled>
                Coming Soon
              </Button>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Email Notifications</p>
                <p className="text-sm text-muted-foreground">
                  Receive portfolio alerts via email
                </p>
              </div>
              <Button variant="outline" disabled>
                Coming Soon
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
