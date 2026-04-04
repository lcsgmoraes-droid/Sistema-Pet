import CampanhasOperacionaisModals from "./CampanhasOperacionaisModals";
import CampanhasGestaoModals from "./CampanhasGestaoModals";

export default function CampanhasModalsLayer(props) {
  return (
    <>
      <CampanhasOperacionaisModals {...props} />
      <CampanhasGestaoModals {...props} />
    </>
  );
}
