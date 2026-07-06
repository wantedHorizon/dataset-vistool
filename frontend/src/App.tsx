import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { DatasetProvider } from "./context/DatasetContext";
import Home from "./pages/Home";
import AddDataset from "./pages/AddDataset";
import SchemaEditor from "./pages/SchemaEditor";

export default function App() {
  return (
    <DatasetProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/datasets/new" element={<AddDataset />} />
          <Route path="/datasets/:id/schema" element={<SchemaEditor />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </DatasetProvider>
  );
}
