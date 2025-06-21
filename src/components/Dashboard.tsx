import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Header } from './Header'
import { PlatformSelector } from './PlatformSelector'
import { ContentCreator } from './ContentCreator'
import { ScheduleManager } from './ScheduleManager'
import { Analytics } from './Analytics'
import { Settings } from './Settings'
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs'

export function Dashboard() {
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([])
  const [activeTab, setActiveTab] = useState('create')

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      <Header />
      
      <main className="container mx-auto px-4 py-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="space-y-8"
        >
          {/* Welcome Section */}
          <div className="text-center space-y-4">
            <motion.h1 
              className="text-4xl md:text-5xl font-bold gradient-text"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6, delay: 0.2 }}
            >
              Social Media Dashboard
            </motion.h1>
            <motion.p 
              className="text-lg text-slate-600 max-w-2xl mx-auto"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.4 }}
            >
              Manage all your social media platforms from one powerful dashboard. 
              Create, schedule, and analyze your content across TikTok, Facebook, YouTube, and more.
            </motion.p>
          </div>

          {/* Platform Selection */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.6 }}
          >
            <PlatformSelector 
              selectedPlatforms={selectedPlatforms}
              onPlatformChange={setSelectedPlatforms}
            />
          </motion.div>

          {/* Main Content Tabs */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.8 }}
          >
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
              <TabsList className="grid w-full grid-cols-4 lg:w-[600px] mx-auto">
                <TabsTrigger value="create" className="flex items-center gap-2">
                  <span className="text-sm">Create</span>
                </TabsTrigger>
                <TabsTrigger value="schedule" className="flex items-center gap-2">
                  <span className="text-sm">Schedule</span>
                </TabsTrigger>
                <TabsTrigger value="analytics" className="flex items-center gap-2">
                  <span className="text-sm">Analytics</span>
                </TabsTrigger>
                <TabsTrigger value="settings" className="flex items-center gap-2">
                  <span className="text-sm">Settings</span>
                </TabsTrigger>
              </TabsList>

              <div className="mt-8">
                <TabsContent value="create" className="space-y-6">
                  <ContentCreator selectedPlatforms={selectedPlatforms} />
                </TabsContent>

                <TabsContent value="schedule" className="space-y-6">
                  <ScheduleManager />
                </TabsContent>

                <TabsContent value="analytics" className="space-y-6">
                  <Analytics />
                </TabsContent>

                <TabsContent value="settings" className="space-y-6">
                  <Settings />
                </TabsContent>
              </div>
            </Tabs>
          </motion.div>
        </motion.div>
      </main>
    </div>
  )
}