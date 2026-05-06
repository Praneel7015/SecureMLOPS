import re

with open("frontend/src/app/components/Dashboard.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the layout
old_layout = """      {/* Main Content */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* Input Panel */}
        <div className={`input-panel bg-card border-b lg:border-b-0 lg:border-r border-border transition-all duration-300 ${isInputPanelOpen ? 'lg:w-96' : 'lg:w-0'} overflow-hidden`}>
          <div className="p-6 space-y-6">"""

new_layout = """      {/* Main Content */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* Responsive Content Container */}
        <ResizablePanelGroup direction="horizontal" className="hidden lg:flex w-full h-full">
          {/* Input Panel Desktop */}
          {isInputPanelOpen && (
            <>
              <ResizablePanel defaultSize={35} minSize={25} maxSize={50} className="bg-card">
                <ScrollArea className="h-full">
                  <div className="p-6 space-y-6">"""

if old_layout in content:
    content = content.replace(old_layout, new_layout)
else:
    print("Failed to find old_layout")

# Replace the split part between input form and main area
old_split = """              </Button>
            </form>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 overflow-auto p-6 space-y-6">"""

new_split = """              </Button>
            </form>
                  </div>
                </ScrollArea>
              </ResizablePanel>
              <ResizableHandle withHandle />
            </>
          )}

          {/* Main Content Area Desktop */}
          <ResizablePanel defaultSize={isInputPanelOpen ? 65 : 100} className="bg-background">
            <ScrollArea className="h-full">
              <div className="p-6 space-y-6">"""

if old_split in content:
    content = content.replace(old_split, new_split)
else:
    print("Failed to find old_split")


old_end = """          </Card>
        </div>
      </div>
    </div>
  );
}"""

new_end = """          </Card>
              </div>
            </ScrollArea>
          </ResizablePanel>
        </ResizablePanelGroup>

        {/* Mobile View - Fallback to standard flex flow for narrow screens */}
        <div className="flex-1 flex flex-col lg:hidden overflow-auto p-6 space-y-6">
           <Alert className="bg-muted text-muted-foreground border-border">
             <AlertCircle className="h-4 w-4" />
             <AlertTitle>Notice</AlertTitle>
             <AlertDescription>
               Please use a desktop browser to access the full analysis dashboard interface with input controls.
             </AlertDescription>
           </Alert>
        </div>

      </div>
    </div>
  );
}"""

if old_end in content:
    content = content.replace(old_end, new_end)
else:
    print("Failed to find old_end")

with open("frontend/src/app/components/Dashboard.tsx", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated successfully")