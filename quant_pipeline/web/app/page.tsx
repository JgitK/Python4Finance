import { Footer } from "@/components/Footer";
import { MenuBar } from "@/components/MenuBar";
import { BasketTray } from "@/components/ui";
import Opening from "@/components/chapters/00-opening";
import PickChapter from "@/components/chapters/01-pick";
import IchimokuChapter from "@/components/chapters/02-ichimoku";
import RiskChapter from "@/components/chapters/03-risk";
import TogetherChapter from "@/components/chapters/04-together";
import FrontierChapter from "@/components/chapters/05-frontier";
import MoneyChapter from "@/components/chapters/06-money";
import TrustChapter from "@/components/chapters/07-trust";
import { Providers } from "./providers";

export default function Home() {
  return (
    <Providers>
      <MenuBar />
      <main>
        <Opening />
        <PickChapter />
        <IchimokuChapter />
        <RiskChapter />
        <TogetherChapter />
        <FrontierChapter />
        <MoneyChapter />
        <TrustChapter />
      </main>
      <Footer />
      <BasketTray />
    </Providers>
  );
}
