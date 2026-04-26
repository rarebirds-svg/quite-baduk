"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { Sheet, SheetTrigger, SheetContent } from "@/components/ui/sheet";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import {
  TooltipProvider,
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { BrandMark } from "@/components/editorial/BrandMark";
import { Hero } from "@/components/editorial/Hero";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { StatFigure } from "@/components/editorial/StatFigure";
import { DataBlock } from "@/components/editorial/DataBlock";
import { PlayerCaption } from "@/components/editorial/PlayerCaption";
import { KeybindHint } from "@/components/editorial/KeybindHint";
import { EmptyState } from "@/components/editorial/EmptyState";
import { Spinner } from "@/components/editorial/Spinner";
import {
  IconPass,
  IconResign,
  IconUndo,
  IconHint,
  IconHandicap,
} from "@/components/editorial/icons";
import { toast } from "sonner";
import { useTheme } from "next-themes";

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-4 py-8">
      <RuleDivider label={title} weight="strong" />
      <div className="flex flex-wrap items-start gap-6">{children}</div>
    </section>
  );
}

export default function ComponentsCatalog() {
  const { theme, setTheme } = useTheme();
  const [togglePosition, setTogglePosition] = useState("light");

  return (
    <TooltipProvider>
      <div className="flex flex-col gap-6 pb-16">
        <Hero
          title="Component Catalog"
          subtitle="Internal visual smoke test for the Editorial Hardcover design system."
          volume="DEV"
        />

        <div className="flex gap-3">
          <Button
            onClick={() => setTheme("light")}
            variant={theme === "light" ? "default" : "outline"}
            size="sm"
          >
            Day
          </Button>
          <Button
            onClick={() => setTheme("dark")}
            variant={theme === "dark" ? "default" : "outline"}
            size="sm"
          >
            Night
          </Button>
          <Button
            onClick={() => setTheme("system")}
            variant={theme === "system" ? "default" : "outline"}
            size="sm"
          >
            System
          </Button>
        </div>

        <Section title="Buttons">
          <Button>Default</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="link">Link</Button>
          <Button variant="destructive">Destructive</Button>
          <Button size="sm">Small</Button>
          <Button size="lg">Large</Button>
          <Button disabled>Disabled</Button>
        </Section>

        <Section title="BrandMark">
          <BrandMark size={16} />
          <BrandMark size={20} />
          <BrandMark size={24} />
          <BrandMark size={32} />
        </Section>

        <Section title="Stats & Data">
          <StatFigure value="62.3" unit="%" label="Win Rate" trend="up" />
          <StatFigure value={47} label="Move" />
          <StatFigure value="04:22" label="Time" />
          <DataBlock label="Captures" value="● 3  ○ 2" />
          <DataBlock label="Board" value="9 × 9" description="Komi 6.5" />
        </Section>

        <Section title="Players">
          <PlayerCaption
            color="black"
            name="rarebirds"
            rank="1단"
            subtitle="0:21 used"
          />
          <PlayerCaption
            color="white"
            name="KataGo"
            rank="Human-SL 3d"
            subtitle="thinking..."
          />
        </Section>

        <Section title="Inputs">
          <div className="flex flex-col gap-2 w-64">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" placeholder="you@example.com" />
          </div>
          <div className="flex flex-col gap-2 w-64">
            <Label htmlFor="err">Invalid field</Label>
            <Input id="err" aria-invalid="true" defaultValue="…" />
          </div>
        </Section>

        <Section title="Select">
          <Select>
            <SelectTrigger className="w-60">
              <SelectValue placeholder="Board size" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="9">9 × 9</SelectItem>
              <SelectItem value="13">13 × 13</SelectItem>
              <SelectItem value="19">19 × 19</SelectItem>
            </SelectContent>
          </Select>
        </Section>

        <Section title="Dialog & Sheet">
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="outline">Open Dialog</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>기권하시겠습니까?</DialogTitle>
                <DialogDescription>
                  현재 대국을 기권으로 종료합니다. 기보는 저장됩니다.
                </DialogDescription>
              </DialogHeader>
              <div className="flex gap-2 justify-end">
                <Button variant="ghost">취소</Button>
                <Button variant="destructive">기권</Button>
              </div>
            </DialogContent>
          </Dialog>
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="outline">Open Sheet</Button>
            </SheetTrigger>
            <SheetContent side="right">
              <h3 className="font-serif text-xl font-semibold mb-4">Analysis</h3>
              <StatFigure value="62.3" unit="%" label="Win Rate" trend="up" />
            </SheetContent>
          </Sheet>
        </Section>

        <Section title="DropdownMenu">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost">User</Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuLabel>Account</DropdownMenuLabel>
              <DropdownMenuItem>Profile</DropdownMenuItem>
              <DropdownMenuItem>Games</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem>Logout</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </Section>

        <Section title="Tabs & ToggleGroup">
          <Tabs defaultValue="play" className="w-[400px]">
            <TabsList>
              <TabsTrigger value="play">Play</TabsTrigger>
              <TabsTrigger value="review">Review</TabsTrigger>
              <TabsTrigger value="history">History</TabsTrigger>
            </TabsList>
            <TabsContent value="play">Play content</TabsContent>
            <TabsContent value="review">Review content</TabsContent>
            <TabsContent value="history">History content</TabsContent>
          </Tabs>
          <ToggleGroup
            type="single"
            value={togglePosition}
            onValueChange={(v) => v && setTogglePosition(v)}
          >
            <ToggleGroupItem value="light">Day</ToggleGroupItem>
            <ToggleGroupItem value="dark">Night</ToggleGroupItem>
            <ToggleGroupItem value="system">System</ToggleGroupItem>
          </ToggleGroup>
        </Section>

        <Section title="Tooltip + Keybinds">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="outline">Hover me</Button>
            </TooltipTrigger>
            <TooltipContent>Press Enter</TooltipContent>
          </Tooltip>
          <KeybindHint keys={["P"]} description="Pass" />
          <KeybindHint keys={["⌘", "K"]} description="Command" />
        </Section>

        <Section title="Icons">
          <IconPass /> <IconResign /> <IconUndo /> <IconHint /> <IconHandicap />
        </Section>

        <Section title="Toast">
          <Button onClick={() => toast("착수 완료 — E4")}>Trigger toast</Button>
          <Button
            onClick={() => toast.error("연결이 끊겼습니다.")}
            variant="destructive"
          >
            Error toast
          </Button>
        </Section>

        <Section title="Spinner">
          <div className="w-64">
            <Spinner />
          </div>
          <div className="w-64">
            <Spinner size="sm" />
          </div>
        </Section>

        <Section title="EmptyState">
          <div className="w-full">
            <EmptyState
              icon={<BrandMark size={32} className="opacity-40" />}
              title="아직 대국이 없습니다"
              description="첫 대국을 시작해 기보를 쌓아보세요."
              action={<Button>새 대국</Button>}
            />
          </div>
        </Section>

        <Section title="Card">
          <Card className="w-80">
            <CardHeader>
              <CardTitle>최근 대국</CardTitle>
            </CardHeader>
            <CardContent>
              <PlayerCaption color="black" name="rarebirds" rank="1단" />
              <Separator className="my-3" />
              <div className="font-mono text-xs text-ink-mute">
                2026-04-19 · 9×9 · 승
              </div>
            </CardContent>
          </Card>
        </Section>
      </div>
    </TooltipProvider>
  );
}
