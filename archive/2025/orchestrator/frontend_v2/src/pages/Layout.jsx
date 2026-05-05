
import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/useAuth";
import { useSocket } from "@/contexts/useSocket";
import { useRundown } from "@/contexts/useRundown";
import { createPageUrl } from "@/utils";
import {
  Radio,
  Settings,
  Wifi,
  WifiOff,
  Menu,
  X
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

const navigationItems = [
  { title: "Live", url: createPageUrl("Live"), icon: Radio, description: "Control Room" },
  // { title: "Chat", url: createPageUrl("Console"), icon: MessageSquare, description: "Full Chat" },
  // { title: "Agents", url: createPageUrl("Agents"), icon: Users, description: "AI Agents" },
  // { title: "Tasks", url: createPageUrl("Tasks"), icon: ListChecks, description: "Task History" },
  // { title: "Schedule", url: createPageUrl("Schedule"), icon: CalendarDays, description: "Rundown" },
  // { title: "Media", url: createPageUrl("Media"), icon: Play, description: "Preview" },
  // { title: "Status", url: createPageUrl("Status"), icon: Wifi, description: "System" },
  // { title: "Contacts", url: createPageUrl("Contacts"), icon: BookUser, description: "Teams" },
  { title: "Settings", url: createPageUrl("Settings"), icon: Settings, description: "Config" }
];

const visibleNavItems = navigationItems.filter(item => item.title !== 'Settings');
const settingsNavItem = navigationItems.find(item => item.title === 'Settings');


export default function Layout({ children }) {
  const location = useLocation();
  const { currentUser, signOut, setIsUpgrading } = useAuth();
  const { connectionStatus } = useSocket();
  const { rundownSystem, updateRundownSystem } = useRundown();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleRundownChange = (checked) => {
    const newRundownSystem = checked ? "sofie" : "cuez";
    updateRundownSystem(newRundownSystem);
  };

  return (
    <div className="min-h-screen bg-[#0D0B12] text-[#E6E1E5]">
      {/* Header */}
      <header className="bg-[#1C1A22] border-b border-white/8 px-4 sm:px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 sm:gap-6">
            {/* Logo and Title */}
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-r from-[#FF2D86] to-[#FFC857] rounded-lg flex items-center justify-center">
                <Radio className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg sm:text-xl font-bold">LiveAgents</h1>
                <p className="text-xs text-[#A6A0AA] hidden sm:block">AI Assistant Control</p>
              </div>
            </div>

            {/* Desktop Navigation - Hidden on screens < 1044px */}
            <nav className="hidden 2xl:flex items-center gap-1 ml-8">
              {visibleNavItems.map((item) =>
              <Link
                key={item.title}
                to={item.url}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-all duration-200 group ${
                location.pathname === item.url || item.url === createPageUrl("Live") && location.pathname === "/" ?
                "bg-[#FF2D86]/20 text-[#FF2D86]" :
                "text-[#A6A0AA] hover:text-[#E6E1E5] hover:bg-white/5"}`
                }>

                  <item.icon className="w-4 h-4" />
                  <span className="text-sm font-medium whitespace-nowrap">{item.title}</span>
                </Link>
              )}
            </nav>
          </div>

          <div className="flex items-center gap-2 sm:gap-4">
            <div className="sm:flex items-center space-x-2 mr-4">
              <Label htmlFor="rundown-system-toggle" className={rundownSystem === 'cuez' ? 'text-green-400 font-bold' : 'text-gray-400'}>CUEZ</Label>
              <Switch
                id="rundown-system-toggle"
                data-testid="rundown-system-toggle"
                checked={rundownSystem === "sofie"}
                onCheckedChange={handleRundownChange}
              />
              <Label htmlFor="rundown-system-toggle" className={rundownSystem === 'sofie' ? 'text-green-400 font-bold' : 'text-gray-400'}>SOFIE</Label>
            </div>

            {settingsNavItem &&
              <Link
                key={settingsNavItem.title}
                to={settingsNavItem.url}
                className={`hidden 2xl:flex items-center gap-2 px-3 py-2 rounded-lg transition-all duration-200 group ${
                location.pathname === settingsNavItem.url ?
                "bg-[#FF2D86]/20 text-[#FF2D86]" :
                "text-[#A6A0AA] hover:text-[#E6E1E5] hover:bg-white/5"}`
                }>
                  <settingsNavItem.icon className="w-4 h-4" />
                  <span className="text-sm font-medium whitespace-nowrap">{settingsNavItem.title}</span>
                </Link>
            }

            {currentUser && currentUser.isAnonymous && (
              <Button
                variant="outline"
                size="sm"
                className="text-foreground"
                onClick={() => {
                  setIsUpgrading(true);
                  signOut();
                }}
              >
                Login with Google
              </Button>
            )}
            <Button variant="outline" size="sm" className="text-foreground" onClick={() => signOut()}>
              Sign Out
            </Button>
            {/* Connection Status - Responsive sizing */}
            <div className="hidden sm:flex items-center gap-2">
              {connectionStatus === "connected" ?
              <>
                  <Wifi className="w-4 h-4 text-teal-500" />
                  <Badge variant="outline" className="border-teal-500/30 text-teal-500 bg-teal-500/10 text-xs">
                    Connected
                  </Badge>
                </> :
              connectionStatus === "connecting" ?
              <>
                  <div className="w-4 h-4 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin" />
                  <Badge variant="outline" className="border-yellow-500/30 text-yellow-500 bg-yellow-500/10 text-xs">
                    Connecting
                  </Badge>
                </> :

              <>
                  <WifiOff className="w-4 h-4 text-destructive" />
                  <Badge variant="outline" className="border-destructive/30 text-destructive bg-destructive/10 text-xs">
                    Disconnected
                  </Badge>
                </>
              }
            </div>

            {/* Mobile menu button - Visible on screens < 1044px */}
            <Button
              variant="ghost"
              size="sm" className="bg-fuchsia-600 text-[#ffffff] px-3 text-sm font-medium inline-flex items-center justify-center gap-2 whitespace-nowrap ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent h-9 rounded-md 2xl:hidden hover:text-[#1a1a1a]"

              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>

              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </Button>
          </div>
        </div>

        {/* Mobile/Tablet Navigation Dropdown */}
        {mobileMenuOpen &&
        <div className="2xl:hidden mt-4 pb-4 border-t border-white/8 pt-4">
            <nav className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
              {navigationItems.map((item) =>
            <Link
              key={item.title}
              to={item.url}
              onClick={() => setMobileMenuOpen(false)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-all duration-200 ${
              location.pathname === item.url || item.url === createPageUrl("Live") && location.pathname === "/" ?
              "bg-[#FF2D86]/20 text-[#FF2D86]" :
              "text-[#A6A0AA] hover:text-[#E6E1E5] hover:bg-white/5"}`
              }>

                  <item.icon className="w-4 h-4" />
                  <span className="text-sm font-medium">{item.title}</span>
                </Link>
            )}
            </nav>

            <div className="mt-4 pt-4 border-t border-white/8 flex justify-center">
              <div className="flex items-center space-x-2">
                <Label htmlFor="rundown-system-toggle-mobile" className={rundownSystem === 'cuez' ? 'text-green-400 font-bold' : 'text-gray-400'}>CUEZ</Label>
                <Switch
                  id="rundown-system-toggle-mobile"
                  checked={rundownSystem === "sofie"}
                  onCheckedChange={handleRundownChange}
                />
                <Label htmlFor="rundown-system-toggle-mobile" className={rundownSystem === 'sofie' ? 'text-green-400 font-bold' : 'text-gray-400'}>SOFIE</Label>
              </div>
            </div>

            {/* Mobile Connection Status */}
            <div className="sm:hidden mt-4 pt-4 border-t border-white/8 flex items-center justify-center gap-2">
              {connectionStatus === "connected" ?
            <>
                  <Wifi className="w-4 h-4 text-teal-500" />
                  <Badge variant="outline" className="border-teal-500/30 text-teal-500 bg-teal-500/10 text-xs">
                    Connected
                  </Badge>
                </> :
            connectionStatus === "connecting" ?
            <>
                  <div className="w-4 h-4 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin" />
                  <Badge variant="outline" className="border-yellow-500/30 text-yellow-500 bg-yellow-500/10 text-xs">
                    Connecting
                  </Badge>
                </> :

            <>
                  <WifiOff className="w-4 h-4 text-destructive" />
                  <Badge variant="outline" className="border-destructive/30 text-destructive bg-destructive/10 text-xs">
                    Disconnected
                  </Badge>
                </>
            }
            </div>
          </div>
        }
      </header>

      {/* Main Content */}
      <main className="flex-1">
        {children}
      </main>
    </div>);

}
