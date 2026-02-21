import { NewChatButton } from './NewChatButton.jsx';
import { DemoNotice } from './DemoNotice.jsx';

export function Header({ onNewChat, onReturnHome }) {
  return (
    <header className="sticky top-0 z-40 bg-[#FFFFFF] shadow-sm">
      <div className="border-b border-[#E2E8F0]">
        <div className="mx-auto flex h-[72px] max-w-full items-center justify-between px-[24px]">
          <button
            onClick={onReturnHome}
            className="flex items-center gap-[12px] border-0 bg-transparent p-0"
            aria-label="Return to home"
          >
            <div className="flex h-[32px] w-[32px] flex-none items-center justify-center rounded-[8px] bg-gradient-to-br from-[#0F172A] to-[#0D9488]">
              <span className="text-[14px] font-bold text-[#FFFFFF]">CF</span>
            </div>
            <span className="font-sans text-[18px] font-semibold text-[#0F172A]">CourseFlow</span>
          </button>

          <NewChatButton onNewChat={onNewChat} />
        </div>
      </div>
      <DemoNotice variant="collapsible" />
    </header>
  );
}