import { createBrowserRouter, Navigate, Outlet, RouterProvider } from "react-router-dom";
import { DatasetProvider } from "./context/DatasetContext";
import Home from "./pages/Home";
import Datasets from "./pages/Datasets";
import AddDataset from "./pages/AddDataset";
import SchemaEditor from "./pages/SchemaEditor";

const router = createBrowserRouter([
  {
    element: (
      <DatasetProvider>
        <Outlet />
      </DatasetProvider>
    ),
    children: [
      { path: "/", element: <Home /> },
      { path: "/datasets", element: <Datasets /> },
      { path: "/datasets/new", element: <AddDataset /> },
      { path: "/datasets/:id/schema", element: <SchemaEditor /> },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
