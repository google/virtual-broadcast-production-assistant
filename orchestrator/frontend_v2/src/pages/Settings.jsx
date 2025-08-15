import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Settings as SettingsIcon, Save, RotateCcw } from "lucide-react";

const defaultSettings = {
  websocketUrl: "ws://localhost:8000",
  audioMode: true,
  pushToTalk: false,
  themeDensity: "comfortable",
  showDemoTelemetry: false,
  autoReconnect: true,
  reconnectInterval: 5
};

export default function Settings() {
  const [settings, setSettings] = useState(defaultSettings);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    // Load settings from localStorage
    const saved = localStorage.getItem('orchestrator-settings');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setSettings({ ...defaultSettings, ...parsed });
      } catch (error) {
        console.error('Failed to parse settings:', error);
      }
    }
  }, []);

  const handleSettingChange = (key, value) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  const handleSave = () => {
    localStorage.setItem('orchestrator-settings', JSON.stringify(settings));
    setHasChanges(false);
  };

  const handleReset = () => {
    setSettings(defaultSettings);
    localStorage.removeItem('orchestrator-settings');
    setHasChanges(true);
  };

  return (
    <div className="min-h-[calc(100vh-80px)] bg-[#0D0B12] p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-[#E6E1E5] mb-2">Settings</h1>
            <p className="text-[#A6A0AA]">Configure your Orchestrator experience</p>
          </div>
          
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              onClick={handleReset} className="bg-background text-slate-900 px-4 py-2 text-sm font-medium inline-flex items-center justify-center whitespace-nowrap rounded-md ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 border border-input hover:bg-accent hover:text-accent-foreground h-10 gap-2">


              <RotateCcw className="w-4 h-4" />
              Reset to Defaults
            </Button>
            <Button
              onClick={handleSave}
              disabled={!hasChanges}
              className="bg-[#FF2D86] hover:bg-[#FF2D86]/90 gap-2">

              <Save className="w-4 h-4" />
              Save Changes
            </Button>
          </div>
        </div>

        {/* Settings Cards */}
        <div className="space-y-6">
          {/* Connection Settings */}
          <Card className="bg-gradient-to-br from-[#1C1A22] to-[#2A2731] border-white/10">
            <CardHeader>
              <CardTitle className="text-[#E6E1E5]">Connection Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="websocket-url" className="text-[#E6E1E5]">
                  WebSocket Base URL
                </Label>
                <Input
                  id="websocket-url"
                  value={settings.websocketUrl}
                  onChange={(e) => handleSettingChange('websocketUrl', e.target.value)}
                  className="bg-white/5 border-white/10 text-[#E6E1E5]"
                  placeholder="ws://localhost:8000" />

                <p className="text-xs text-[#A6A0AA]">
                  Override the default WebSocket endpoint for development or custom deployments
                </p>
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <Label htmlFor="auto-reconnect" className="text-[#E6E1E5]">
                    Auto Reconnect
                  </Label>
                  <p className="text-xs text-[#A6A0AA]">
                    Automatically reconnect when connection is lost
                  </p>
                </div>
                <Switch
                  id="auto-reconnect"
                  checked={settings.autoReconnect}
                  onCheckedChange={(checked) => handleSettingChange('autoReconnect', checked)} />

              </div>

              {settings.autoReconnect &&
              <div className="space-y-2">
                  <Label htmlFor="reconnect-interval" className="text-[#E6E1E5]">
                    Reconnect Interval (seconds)
                  </Label>
                  <Select
                  value={settings.reconnectInterval.toString()}
                  onValueChange={(value) => handleSettingChange('reconnectInterval', parseInt(value))}>

                    <SelectTrigger className="bg-white/5 border-white/10 text-[#E6E1E5]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">1 second</SelectItem>
                      <SelectItem value="3">3 seconds</SelectItem>
                      <SelectItem value="5">5 seconds</SelectItem>
                      <SelectItem value="10">10 seconds</SelectItem>
                      <SelectItem value="30">30 seconds</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              }
            </CardContent>
          </Card>

          {/* Audio Settings */}
          <Card className="bg-gradient-to-br from-[#1C1A22] to-[#2A2731] border-white/10">
            <CardHeader>
              <CardTitle className="text-[#E6E1E5]">Audio Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <Label htmlFor="audio-mode" className="text-[#E6E1E5]">
                    Audio Mode
                  </Label>
                  <p className="text-xs text-[#A6A0AA]">
                    Enable voice communication with AI agents
                  </p>
                </div>
                <Switch
                  id="audio-mode"
                  checked={settings.audioMode}
                  onCheckedChange={(checked) => handleSettingChange('audioMode', checked)} />

              </div>

              {settings.audioMode &&
              <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label htmlFor="push-to-talk" className="text-[#E6E1E5]">
                      Push-to-Talk
                    </Label>
                    <p className="text-xs text-[#A6A0AA]">
                      Hold space bar to transmit audio instead of toggle mode
                    </p>
                  </div>
                  <Switch
                  id="push-to-talk"
                  checked={settings.pushToTalk}
                  onCheckedChange={(checked) => handleSettingChange('pushToTalk', checked)} />

                </div>
              }
            </CardContent>
          </Card>

          {/* Interface Settings */}
          <Card className="bg-gradient-to-br from-[#1C1A22] to-[#2A2731] border-white/10">
            <CardHeader>
              <CardTitle className="text-[#E6E1E5]">Interface Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="theme-density" className="text-[#E6E1E5]">
                  Theme Density
                </Label>
                <Select
                  value={settings.themeDensity}
                  onValueChange={(value) => handleSettingChange('themeDensity', value)}>

                  <SelectTrigger className="bg-white/5 border-white/10 text-[#E6E1E5]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="compact">Compact</SelectItem>
                    <SelectItem value="comfortable">Comfortable</SelectItem>
                    <SelectItem value="spacious">Spacious</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-[#A6A0AA]">
                  Adjust the spacing and density of UI elements
                </p>
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <Label htmlFor="demo-telemetry" className="text-[#E6E1E5]">
                    Show Demo Telemetry
                  </Label>
                  <p className="text-xs text-[#A6A0AA]">
                    Display sample telemetry data when no real data is available
                  </p>
                </div>
                <Switch
                  id="demo-telemetry"
                  checked={settings.showDemoTelemetry}
                  onCheckedChange={(checked) => handleSettingChange('showDemoTelemetry', checked)} />

              </div>
            </CardContent>
          </Card>

          {/* System Information */}
          <Card className="bg-gradient-to-br from-[#1C1A22] to-[#2A2731] border-white/10">
            <CardHeader>
              <CardTitle className="text-[#E6E1E5]">System Information</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-[#A6A0AA]">Version:</span>
                  <span className="ml-2 text-[#E6E1E5]">v1.0.0-beta</span>
                </div>
                <div>
                  <span className="text-[#A6A0AA]">Build Date:</span>
                  <span className="ml-2 text-[#E6E1E5]">2024-01-15</span>
                </div>
                <div>
                  <span className="text-[#A6A0AA]">Environment:</span>
                  <span className="ml-2 text-[#E6E1E5]">Development</span>
                </div>
                <div>
                  <span className="text-[#A6A0AA]">User Agent:</span>
                  <span className="ml-2 text-[#E6E1E5]">Chrome/120.0.0.0</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Save Notice */}
        {hasChanges &&
        <div className="fixed bottom-6 right-6 bg-[#1C1A22] border border-[#FF2D86]/30 rounded-lg p-4 shadow-lg">
            <div className="flex items-center gap-3">
              <SettingsIcon className="w-5 h-5 text-[#FF2D86]" />
              <p className="text-[#E6E1E5] text-sm">You have unsaved changes</p>
              <Button
              onClick={handleSave}
              size="sm"
              className="bg-[#FF2D86] hover:bg-[#FF2D86]/90">

                Save
              </Button>
            </div>
          </div>
        }
      </div>
    </div>);

}