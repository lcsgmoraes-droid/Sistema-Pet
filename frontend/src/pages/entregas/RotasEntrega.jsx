import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function RotasEntrega() {
  const navigate = useNavigate();
  
  useEffect(() => {
    // Redirecionar para a nova página de entregas abertas
    navigate("/entregas/abertas", { replace: true });
  }, [navigate]);

  return (
    <div className="page">
      <p>Redirecionando para entregas abertas...</p>
    </div>
  );
}
