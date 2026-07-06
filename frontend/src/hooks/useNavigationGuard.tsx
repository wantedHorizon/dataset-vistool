import { useEffect, useState } from "react";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from "@mui/material";
import { useBlocker } from "react-router-dom";

export function useNavigationGuard(active: boolean) {
  const blocker = useBlocker(active);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (blocker.state === "blocked") {
      setOpen(true);
    }
  }, [blocker.state]);

  useEffect(() => {
    if (!active) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [active]);

  const handleStay = () => {
    setOpen(false);
    if (blocker.state === "blocked") {
      blocker.reset();
    }
  };

  const handleLeave = () => {
    setOpen(false);
    if (blocker.state === "blocked") {
      blocker.proceed();
    }
  };

  const dialog = (
    <Dialog open={open} onClose={handleStay}>
      <DialogTitle>Download in progress</DialogTitle>
      <DialogContent>
        <DialogContentText>
          A dataset download is still running. Leave this page anyway?
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleStay}>Stay</Button>
        <Button color="warning" onClick={handleLeave}>
          Leave anyway
        </Button>
      </DialogActions>
    </Dialog>
  );

  return dialog;
}
