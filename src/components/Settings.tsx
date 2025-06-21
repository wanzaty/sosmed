import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Settings as SettingsIcon, User, Bell, Shield, Palette, Globe, Link } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Switch } from './ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs'
import { Badge } from './ui/badge'

const connectedAccounts = [
  { platform: 'TikTok', username: '@yourhandle', connected: true, icon: '🎵' },
  { platform: 'Facebook', username: 'Your Page', connected: true, icon: '📘' },
  { platform: 'Instagram', username: '@yourhandle', connected: false, icon: '📸' },
  { platform: 'YouTube', username: 'Your Channel', connected: true, icon: '📺' },
  { platform: 'Twitter', username: '@yourhandle', connected: false, icon: '🐦' },
  { platform: 'LinkedIn', username: 'Your Profile', connected: false, icon: '💼' }
]

export function Settings() {
  const [notifications, setNotifications] = useState({
    postPublished: true,
    scheduledReminder: true,
    engagementAlerts: false,
    weeklyReport: true
  })

  const [profile, setProfile] = useState({
    name: 'John Doe',
    email: 'john@example.com',
    timezone: 'UTC-5'
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-slate-800">Settings</h2>
        <p className="text-slate-600">Manage your account and platform connections</p>
      </div>

      <Tabs defaultValue="profile" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="profile" className="flex items-center gap-2">
            <User className="w-4 h-4" />
            Profile
          </TabsTrigger>
          <TabsTrigger value="accounts" className="flex items-center gap-2">
            <Link className="w-4 h-4" />
            Accounts
          </TabsTrigger>
          <TabsTrigger value="notifications" className="flex items-center gap-2">
            <Bell className="w-4 h-4" />
            Notifications
          </TabsTrigger>
          <TabsTrigger value="preferences" className="flex items-center gap-2">
            <SettingsIcon className="w-4 h-4" />
            Preferences
          </TabsTrigger>
        </TabsList>

        <div className="mt-6">
          {/* Profile Settings */}
          <TabsContent value="profile" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="w-5 h-5" />
                  Profile Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Full Name</Label>
                    <Input
                      id="name"
                      value={profile.name}
                      onChange={(e) => setProfile(prev => ({ ...prev, name: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email Address</Label>
                    <Input
                      id="email"
                      type="email"
                      value={profile.email}
                      onChange={(e) => setProfile(prev => ({ ...prev, email: e.target.value }))}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="timezone">Timezone</Label>
                  <Input
                    id="timezone"
                    value={profile.timezone}
                    onChange={(e) => setProfile(prev => ({ ...prev, timezone: e.target.value }))}
                  />
                </div>
                <Button>Save Changes</Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="w-5 h-5" />
                  Security
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Button variant="outline">Change Password</Button>
                <Button variant="outline">Enable Two-Factor Authentication</Button>
                <Button variant="outline" className="text-red-600 hover:text-red-700">
                  Delete Account
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Connected Accounts */}
          <TabsContent value="accounts" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Link className="w-5 h-5" />
                  Connected Accounts
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {connectedAccounts.map((account, index) => (
                    <motion.div
                      key={account.platform}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, delay: index * 0.1 }}
                      className="flex items-center justify-between p-4 bg-slate-50 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <div className="text-2xl">{account.icon}</div>
                        <div>
                          <h4 className="font-semibold">{account.platform}</h4>
                          <p className="text-sm text-slate-600">{account.username}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        {account.connected ? (
                          <Badge className="bg-green-100 text-green-800">Connected</Badge>
                        ) : (
                          <Badge variant="outline">Not Connected</Badge>
                        )}
                        <Button
                          variant={account.connected ? "outline" : "default"}
                          size="sm"
                        >
                          {account.connected ? 'Disconnect' : 'Connect'}
                        </Button>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Notifications */}
          <TabsContent value="notifications" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bell className="w-5 h-5" />
                  Notification Preferences
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium">Post Published</h4>
                    <p className="text-sm text-slate-600">Get notified when your posts are published</p>
                  </div>
                  <Switch
                    checked={notifications.postPublished}
                    onCheckedChange={(checked) => 
                      setNotifications(prev => ({ ...prev, postPublished: checked }))
                    }
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium">Scheduled Reminders</h4>
                    <p className="text-sm text-slate-600">Reminders for upcoming scheduled posts</p>
                  </div>
                  <Switch
                    checked={notifications.scheduledReminder}
                    onCheckedChange={(checked) => 
                      setNotifications(prev => ({ ...prev, scheduledReminder: checked }))
                    }
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium">Engagement Alerts</h4>
                    <p className="text-sm text-slate-600">Alerts for high engagement on your posts</p>
                  </div>
                  <Switch
                    checked={notifications.engagementAlerts}
                    onCheckedChange={(checked) => 
                      setNotifications(prev => ({ ...prev, engagementAlerts: checked }))
                    }
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium">Weekly Reports</h4>
                    <p className="text-sm text-slate-600">Weekly analytics and performance reports</p>
                  </div>
                  <Switch
                    checked={notifications.weeklyReport}
                    onCheckedChange={(checked) => 
                      setNotifications(prev => ({ ...prev, weeklyReport: checked }))
                    }
                  />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Preferences */}
          <TabsContent value="preferences" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Palette className="w-5 h-5" />
                  Appearance
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label>Theme</Label>
                  <div className="grid grid-cols-3 gap-3 mt-2">
                    <Button variant="outline" className="justify-start">
                      ☀️ Light
                    </Button>
                    <Button variant="outline" className="justify-start">
                      🌙 Dark
                    </Button>
                    <Button variant="outline" className="justify-start">
                      🔄 Auto
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Globe className="w-5 h-5" />
                  Regional Settings
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Language</Label>
                    <Input value="English (US)" readOnly />
                  </div>
                  <div className="space-y-2">
                    <Label>Date Format</Label>
                    <Input value="MM/DD/YYYY" readOnly />
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </div>
      </Tabs>
    </div>
  )
}