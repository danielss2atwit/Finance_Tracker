import { NavLink } from "react-router-dom";
import "../App.css"; 
import logo from "../assets/logo.png";

export default function Navbar() {
  return (
    <nav className="navbar">
      <div className="navbar-left">
        <img src={logo} alt="App logo" className="navbar-logo-img" />
        <h1 className="navbar-logo-text">MyFinanceApp</h1>
      </div>

      <div className="navbar-links">
        <NavLink to="/" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
          Home
        </NavLink>
        <NavLink to="/transactions" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
          Transactions
        </NavLink>
        <NavLink to="/categories" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
          Categories
        </NavLink>
      </div>
    </nav>
  );
}