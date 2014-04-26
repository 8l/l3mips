---------------------------------------------------------------------------
-- Model of the 64-bit MIPS ISA (MIPS III with some extra instructions)
-- (c) Anthony Fox, University of Cambridge
---------------------------------------------------------------------------

type pAddr = bits(40)
type mAddr = bits(37)

nat PSIZE = 40 -- 40-bit physical memory

-- Code used for SML emulation of MIPS

construct event
{
   w_gpr :: reg * dword
   w_hi :: dword
   w_lo :: dword
   w_c0 :: reg * dword
   w_mem :: pAddr * vAddr * bits(3) * dword
}

declare log :: event list

unit mark (e::event) = log <- e @ log
unit unmark = log <- Tail (log)

--------------------------------------------------
-- Gereral purpose register access
--------------------------------------------------

component GPR (n::reg) :: dword
{
   value = if n == 0 then 0 else gpr(n)
   assign value = when n <> 0 do { gpr(n) <- value; mark (w_gpr (n, value)) }
}

component HI :: dword
{
   value = match hi { case Some (v) => v
                      case None => #UNPREDICTABLE ("HI")
                    }
   assign value = { hi <- Some (value); mark (w_hi (value)) }
}

component LO :: dword
{
   value = match lo { case Some (v) => v
                      case None => #UNPREDICTABLE ("LO")
                    }
   assign value = { lo <- Some (value); mark (w_lo (value)) }
}

--------------------------------------------------
-- CP0 register access
--------------------------------------------------

component CPR (n::nat, reg::bits(5), sel::bits(3)) :: dword
{
   value =
      match n, reg, sel
      {
         case 0,  0, 0 => [CP0.&Index]
         case 0,  1, 0 => [CP0.&Random]
         case 0,  2, 0 =>  CP0.&EntryLo0
         case 0,  3, 0 =>  CP0.&EntryLo1
         case 0,  5, 0 => [CP0.&PageMask]
         case 0,  8, 0 =>  CP0.BadVAddr
         case 0,  9, 0 => [CP0.Count]
         case 0, 10, 0 =>  CP0.&EntryHi
         case 0, 11, 0 => [CP0.Compare]
         case 0, 12, 0 => [CP0.&Status]
         case 0, 13, 0 => [CP0.&Cause]
         case 0, 14, 0 =>  CP0.EPC
         case 0, 15, 0 => [CP0.PRId]
         case 0, 16, 0 => [CP0.&Config]
         case 0, 17, 0 => [CP0.LLAddr]
         case 0, 20, 0 =>  CP0.&XContext
         case 0, 23, 0 => [CP0.Debug]
         case 0, 26, 0 => [CP0.ErrCtl]
         case 0, 30, 0 =>  CP0.ErrorEPC
         case _ => UNKNOWN
      }
   assign value =
   {
      mark (w_c0 (reg, value));
      match n, reg, sel
      {
         case 0,  0, 0 => CP0.Index.Index <- value<5:0>
         case 0,  2, 0 => CP0.&EntryLo0 <- value
         case 0,  3, 0 => CP0.&EntryLo1 <- value
         case 0,  5, 0 => CP0.PageMask.Mask <- value<24:13>
         case 0,  9, 0 => CP0.Count <- value<31:0>
         case 0, 10, 0 => CP0.&EntryHi <- value
         case 0, 11, 0 => CP0.Compare <- value<31:0>
         case 0, 12, 0 => CP0.&Status <- value<31:0>
         case 0, 13, 0 => CP0.&Cause <- value<31:0>
         case 0, 14, 0 => CP0.EPC <- value
         case 0, 16, 0 => CP0.Config.K0 <- value<2:0>
         case 0, 23, 0 => CP0.Debug <- value<31:0>
         case 0, 26, 0 => CP0.ErrCtl <- value<31:0>
         case 0, 30, 0 => CP0.ErrorEPC <- value
         case _ => unmark
      }
   }
}

--------------------------------------------------
-- JTAG UART support
--------------------------------------------------

register JTAG_UART_data :: word
{
  31-16 : RAVAIL    -- Number of characters reamining in read FIFO
     15 : RVALID    -- Indicates whether RW_DATA field is valid
    7-0 : RW_DATA   -- Value to transfer to/from JTAG core
}

register JTAG_UART_control :: word
{
  31-16 : WSPACE    -- Number of spaces available in write FIFO
     10 : AC        -- Indicates that there has been JTAG activity since last
                    -- cleared
      9 : WI        -- Write interrupt is pending
      8 : RI        -- Read interrupt is pending
      1 : WE        -- Write interrupt-enable
      0 : RE        -- Read interrupt-enable
}

record JTAG_UART
{
   base_address      :: mAddr
   data              :: JTAG_UART_data
   control           :: JTAG_UART_control
   read_fifo         :: byte list
   write_fifo        :: byte list
   read_threshold    :: nat
   write_threshold   :: nat
}

declare JTAG_UART :: JTAG_UART

--------------------------------------------------
-- Memory access
--------------------------------------------------

record TLBEntry
{
   Mask :: bits(12)
   R    :: bits(2)
   VPN2 :: bits(27)
   G    :: bool
   ASID :: bits(8)
   PFN0 :: bits(28)
   PFN1 :: bits(28)
   C0   :: bits(3)
   C1   :: bits(3)
   D0   :: bool
   D1   :: bool
   V0   :: bool
   V1   :: bool
}

nat TLBEntries = 16

declare
{
   TLB_direct :: bits(7) -> TLBEntry
   TLB_assoc  :: bits(4) -> TLBEntry
   MEM :: mAddr -> dword                -- physical memory, doubleword access
}

(bits(6) * TLBEntry) list LookupTLB (r::bits(2), vpn2::bits(27)) =
{
   e = TLB_direct (vpn2<6:0>);
   nmask`27 = ~[e.Mask];
   var found = if e.VPN2 && nmask == vpn2 && nmask and e.R == r then
                   list {(16, e)}
               else Nil;
   for i in 0 .. TLBEntries - 1 do
   {
      e = TLB_assoc ([i]);
      nmask`27 = ~[e.Mask];
      when e.VPN2 && nmask == vpn2 && nmask and e.R == r do
         found <- ([i], e) @ found
   };
   return found
}

TLBEntry ModifyTLB (ie::TLBEntry) =
{
   eHi = CP0.EntryHi;
   eLo1 = CP0.EntryLo1;
   eLo0 = CP0.EntryLo0;
   var e = ie;
   e.Mask <- CP0.PageMask.Mask;
   e.R <- eHi.R;
   e.VPN2 <- eHi.VPN2;
   e.ASID <- eHi.ASID;
   e.PFN1 <- eLo1.PFN;
   e.C1 <- eLo1.C;
   e.D1 <- eLo1.D;
   e.V1 <- eLo1.V;
   e.G <- eLo1.G and eLo0.G;
   e.PFN0 <- eLo0.PFN;
   e.C0 <- eLo0.C;
   e.D0 <- eLo0.D;
   e.V0 <- eLo0.V;
   return e
}

pAddr * CCA SignalTLBException (e::ExceptionType, asid::bits(8), vAddr::vAddr) =
{
   r = vAddr<63:62>;
   vpn2 = vAddr<39:13>;
   SignalException (e);
   CP0.BadVAddr <- vAddr;
   CP0.EntryHi.R <- r;
   CP0.EntryHi.VPN2 <- vpn2;
   CP0.EntryHi.ASID <- asid;
   CP0.XContext.R <- r;
   CP0.XContext.BadVPN2 <- vpn2;
   UNKNOWN
}

CCA option * bool CheckSegment (vAddr::vAddr) =
   if UserMode then
      None, vAddr <+ 0x0000_0100_0000_0000      -- xuseg
   else if SupervisorMode then
      None,
      vAddr <+ 0x0000_0100_0000_0000 or         -- xsuseg
      vAddr <=+ 0x4000_0000_0000_0000 and
      vAddr <+  0x4000_0100_0000_0000 or        -- xsseg
      vAddr <=+ 0xFFFF_FFFF_C000_0000 and
      vAddr <+  0xFFFF_FFFF_E000_0000           -- csseg
   else if vAddr <+ 0x0000_0100_0000_0000 then  -- xkuseg
      None, true
   else if 0x4000_0000_0000_0000 <=+ vAddr and
           vAddr <+  0x4000_0100_0000_0000 then -- xksseg
      None, true
   else if 0x8000_0000_0000_0000 <=+ vAddr and
           vAddr <+  0xC000_0000_0000_0000 then -- xkphys (unmapped)
      Some (vAddr<61:59>), vAddr<58:40> == 0
   else if 0xC000_0000_0000_0000 <=+ vAddr and
           vAddr <+  0xC000_00FF_8000_0000 then -- xkseg
      None, true
   else if 0xFFFF_FFFF_8000_0000 <=+ vAddr and
           vAddr <+  0xFFFF_FFFF_A000_0000 then -- ckseg0 (unmapped)
      Some (CP0.Config.K0), true
   else if 0xFFFF_FFFF_A000_0000 <=+ vAddr and
           vAddr <+  0xFFFF_FFFF_C000_0000 then -- ckseg1 (unmapped+uncached)
      Some (2), true
   else
      None, 0xFFFF_FFFF_C000_0000 <=+ vAddr     -- cksseg/ckseg3

pAddr * CCA AddressTranslation (vAddr::vAddr, IorD::IorD, LorS::LorS) =
{
   unmapped, valid = CheckSegment (vAddr);
   if valid then
      match unmapped
      {
         case Some (cca) => vAddr<39:0>, cca
         case None =>
            match LookupTLB (vAddr<63:62>, vAddr<39:13>)
            {
               case Nil =>
                  SignalTLBException (XTLBRefill, CP0.EntryHi.ASID, vAddr)
               case list {(_, e)} =>
                  if e.G or e.ASID == CP0.EntryHi.ASID then
                  {
                     PFN, C, D, V = if vAddr<12> then
                                       e.PFN1, e.C1, e.D1, e.V1
                                    else
                                       e.PFN0, e.C0, e.D0, e.V0;
                     if V then
                        if not D and LorS == STORE then
                           SignalTLBException (Mod, e.ASID, vAddr)
                        else
                           PFN : vAddr<11:0>, C
                     else
                     {
                        exc = if LorS == LOAD then TLBL else TLBS;
                        SignalTLBException (exc, e.ASID, vAddr)
                     }
                  }
                  else
                     SignalTLBException (XTLBRefill, e.ASID, vAddr)
               case _ => #UNPREDICTABLE ("TLB: multiple matches")
            }
      }
   else
   {
      SignalException (if LorS == LOAD then AdEL else AdES);
      UNKNOWN
   }
}

-- Update JTAG_UART memory-map

unit JTAG_UART_write_mm =
   MEM (JTAG_UART.base_address) <- JTAG_UART.&data : JTAG_UART.&control

-- Pimitive memory load

dword LoadMemory (CCA::CCA, AccessLength::bits(3),
                  pAddr::pAddr, vAddr::vAddr, IorD::IorD) =
{  a = pAddr<39:3>;
   var d = MEM (a);
   b = [pAddr<2:0>]::nat;
   when a == JTAG_UART.base_address and b < 4 and 4 <= b + [AccessLength] do
   {
      match JTAG_UART.read_fifo
      {
         case Nil =>
         {
            JTAG_UART.data.RAVAIL <- 0; -- should already hold
            JTAG_UART.data.RVALID <- false
         }
         case h @ t =>
         {
            JTAG_UART.data.RW_DATA <- h;
            JTAG_UART.data.RAVAIL <- [Length (t)];
            JTAG_UART.data.RVALID <- true;
            JTAG_UART.read_fifo <- t
         }
      };
      JTAG_UART.control.RI <- false; -- could have cleared read interrupt
      JTAG_UART_write_mm
   };
   return d
}

word loadWord32 (a::pAddr) =
{
   d = MEM (a<39:3>);
   if a<2> then d<31:0> else d<63:32>
}

-- Pimitive memory store. Big-endian.

unit StoreMemory (CCA::CCA, AccessLength::bits(3), MemElem::dword,
                  pAddr::pAddr, vAddr::vAddr, IorD::IorD) =
{  a = pAddr<39:3>;
   l = 64 - ([AccessLength] + 1 + [pAddr<2:0>]) * 0n8;
   mask`64 = [2 ** (l + ([AccessLength] + 1) * 0n8) - 2 ** l];
   mark (w_mem (pAddr, mask, AccessLength, MemElem));
   if a == JTAG_UART.base_address then
   {
      when mask<39:32> <> 0 do
      {
         JTAG_UART.data.RW_DATA <- MemElem<39:32>;
         JTAG_UART.data.RVALID <- false;
         when JTAG_UART.control.WSPACE <> 0 do
         {
            JTAG_UART.control.WSPACE <- JTAG_UART.control.WSPACE - 1;
            JTAG_UART.write_fifo <-
               JTAG_UART.data.RW_DATA @ JTAG_UART.write_fifo
         }
      };
      when mask<0> do JTAG_UART.control.RE <- MemElem<0>;
      when mask<1> do JTAG_UART.control.WE <- MemElem<1>;
      when mask<10> and MemElem<10> do JTAG_UART.control.AC <- false;
      JTAG_UART.control.WI <-false; -- could have cleared write interrupt
      JTAG_UART_write_mm
   }
   else
      MEM(a) <- MEM(a) && ~mask || MemElem && mask
}

--------------------------------------------------
-- TLB instructions
--------------------------------------------------

define TLBP =
   match LookupTLB (CP0.EntryHi.R, CP0.EntryHi.VPN2)
   {
      case Nil => CP0.Index.P <- true
      case list {(i, e)} =>
         if e.G or e.ASID == CP0.EntryHi.ASID then
         {
            CP0.Index.P <- false;
            CP0.Index.Index <- i
         }
         else
            CP0.Index.P <- true
      case _ => #UNPREDICTABLE ("TLB: multiple matches")
   }

define TLBR =
{
   i = CP0.Index.Index;
   if i >= [TLBEntries] then
      #UNPREDICTABLE ("TLBR: index > TLBEntries - 1")
   else
   {
      e = TLB_assoc ([i]);
      CP0.PageMask.Mask <- e.Mask;
      CP0.EntryHi.R <- e.R;
      CP0.EntryHi.VPN2 <- e.VPN2;
      CP0.EntryHi.ASID <- e.ASID;
      CP0.EntryLo1.PFN <- e.PFN1;
      CP0.EntryLo1.C <- e.C1;
      CP0.EntryLo1.D <- e.D1;
      CP0.EntryLo1.V <- e.V1;
      CP0.EntryLo1.G <- e.G;
      CP0.EntryLo0.PFN <- e.PFN0;
      CP0.EntryLo0.C <- e.C0;
      CP0.EntryLo0.D <- e.D0;
      CP0.EntryLo0.V <- e.V0;
      CP0.EntryLo0.G <- e.G
   }
}

define TLBWI =
{
   i`4 = [CP0.Index.Index];
   if i >= [TLBEntries] then
   {
      j = CP0.EntryHi.VPN2<6:0>;
      TLB_direct (j) <- ModifyTLB (TLB_direct (j))
   }
   else
      TLB_assoc (i) <- ModifyTLB (TLB_assoc (i))
}

define TLBWR =
{
   j = CP0.EntryHi.VPN2<6:0>;
   old = TLB_direct (j);
   TLB_direct (j) <- ModifyTLB (old);
   when old.V0 and old.V1 do TLB_assoc ([CP0.Random.Random]) <- old
}

-------------------------
-- CACHE op, offset(base)
-------------------------
define CACHE (base::reg, opn::bits(5), offset::bits(16)) =
{
   vAddr = GPR(base) + SignExtend(offset);
   pAddr, cca = AddressTranslation (vAddr, DATA, LOAD);
   nothing
}

--------------------------------------------------
-- JTAG UART
--------------------------------------------------

unit JTAG_UART_input (l::byte list) =
{
   match JTAG_UART.read_fifo : l
   {
      case Nil => JTAG_UART.data.RAVAIL <- 0
      case t =>
      {
         JTAG_UART.read_fifo <- t;
         JTAG_UART.data.RAVAIL <- [Length (t)];
         JTAG_UART.control.AC <- true
      }
   };
   JTAG_UART.control.RI <- false;
   JTAG_UART_write_mm
}

byte list JTAG_UART_output =
{
   JTAG_UART.control.AC <- true;
   l = Reverse (JTAG_UART.write_fifo);
   JTAG_UART.write_fifo <- Nil;
   JTAG_UART.control.WSPACE <- -1;
   JTAG_UART.control.WI <- false;
   JTAG_UART_write_mm;
   return l
}

--------------------------------------------------
-- Instruction fetch
--------------------------------------------------

word option Fetch =
{
   log <- Nil;
   CP0.Random.Random <- if CP0.Random.Random == CP0.Wired.Wired then
                           [TLBEntries - 1]
                        else
                            CP0.Random.Random - 1;
   when CP0.Status.IE do
   {
      if CP0.Status.IM<7> and CP0.Compare == CP0.Count then
      {
         CP0.Cause.TI <- true;
         CP0.Cause.IP<7> <- true;
         SignalException (Int)
      }
      else if CP0.Status.IM<2> and JTAG_UART.control.WE and
              not JTAG_UART.control.WI and
              JTAG_UART.write_threshold <= [JTAG_UART.control.WSPACE] then
      {
         JTAG_UART.control.WI <- true;
         JTAG_UART_write_mm;
         CP0.Cause.IP<2> <- true;
         SignalException (Int)
      }
      else if CP0.Status.IM<2> and JTAG_UART.control.RE and
              not JTAG_UART.control.RI and
              JTAG_UART.read_threshold <= [JTAG_UART.data.RAVAIL] then
      {
         JTAG_UART.control.RI <- true;
         JTAG_UART_write_mm;
         CP0.Cause.IP<2> <- true;
         SignalException (Int)
      }
      else if PC<1:0> == 0 then
         nothing
      else
      {
         CP0.BadVAddr <- PC;
         SignalException (AdEL)
      }
   };
   if exceptionSignalled then
      None
   else
   {
      pc, cca = AddressTranslation (PC, INSTRUCTION, LOAD);
      if exceptionSignalled then None else Some (loadWord32 (pc))
   }
}

--------------------------------------------------
-- Initialisation and termination
--------------------------------------------------

TLBEntry initTLB = { var e; e.R <- '10'; return e }

unit addTLB (a::vAddr, i::bits(4)) =
{
   pfn = a<39:12>;
   TLB_assoc(i).VPN2 <- [pfn >>+ 1];
   TLB_assoc(i).R <- '00';
   TLB_assoc(i).G <- true;
   if a<12> then
   {
      TLB_assoc(i).PFN1 <- pfn;
      TLB_assoc(i).C1 <- 2;
      TLB_assoc(i).D1 <- true;
      TLB_assoc(i).V1 <- true
   }
   else
   {
      TLB_assoc(i).PFN0 <- pfn;
      TLB_assoc(i).C0 <- 2;
      TLB_assoc(i).D0 <- true;
      TLB_assoc(i).V0 <- true
   }
}

unit initMips (pc::nat, uart::nat) =
{
   CP0.Config.BE  <- true;      -- big-endian
   CP0.Config.MT  <- 1;         -- standard TLB
   CP0.&Status <- 0x0;          -- reset to kernel mode (interrupts disabled)
   CP0.Status.BEV <- true;
   CP0.Status.KSU <- '00';
   CP0.Status.EXL <- false;
   CP0.Status.ERL <- false;
   CP0.Status.KX <- true;
   CP0.Status.SX <- true;
   CP0.Status.UX <- true;
   CP0.Count <- 0;
   CP0.Compare <- 0;
   CP0.PRId <- 0x400;           -- processor ID
   CP0.Index.P <- false;
   CP0.Index.Index <- 0x0;
   CP0.Random.Random <- 0x10;
   CP0.Wired.Wired <- 0x2;
   JTAG_UART.base_address <- [[uart]::pAddr >>+ 3];
   JTAG_UART.read_threshold <- 0xFF00;
   JTAG_UART.write_threshold <- 0xFFF0;
   JTAG_UART.read_fifo <- Nil;
   JTAG_UART.write_fifo <- Nil;
   JTAG_UART.data.RW_DATA <- 0;
   JTAG_UART.data.RVALID <- false;
   JTAG_UART.data.RAVAIL <- 0;
   JTAG_UART.control.RE <- false;
   JTAG_UART.control.WE <- false;
   JTAG_UART.control.RI <- false;
   JTAG_UART.control.WI <- false;
   JTAG_UART.control.AC <- false;
   JTAG_UART.control.WSPACE <- -1;
   TLB_direct <- InitMap (initTLB);
   TLB_assoc <- InitMap (initTLB);
   BranchDelay <- None;
   BranchTo <- None;
   LLbit <- None;
   hi <- None;
   lo <- None;
   PC <- [pc];
   addTLB (PC, 0);
   addTLB ([JTAG_UART.base_address] : '000', 1);
   MEM <- InitMap (0x0);
   gpr <- InitMap (0xAAAAAAAAAAAAAAAA);
   JTAG_UART_write_mm
}

bool done =
   return
     (match log
      {
         case list {w_c0 (23, _)} => true
         case _ => false
      } or
      match BranchDelay
      {
         case Some (addr) => addr == PC - 8
         case None => false
      })
